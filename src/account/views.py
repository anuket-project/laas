##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


import os
import urllib

import oauth2 as oauth
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import RedirectView, TemplateView, UpdateView
from django.shortcuts import render
from jira import JIRA
from rest_framework.authtoken.models import Token

from account.forms import AccountSettingsForm
from account.jira_util import SignatureMethod_RSA_SHA1
from account.models import UserProfile
from booking.models import Booking
from resource_inventory.models import GenericResourceBundle, ConfigBundle, Image, Host


@method_decorator(login_required, name='dispatch')
class AccountSettingsView(UpdateView):
    model = UserProfile
    form_class = AccountSettingsForm
    template_name_suffix = '_update_form'

    def get_success_url(self):
        messages.add_message(self.request, messages.INFO,
                             'Settings saved')
        return '/'

    def get_object(self, queryset=None):
        return self.request.user.userprofile

    def get_context_data(self, **kwargs):
        token, created = Token.objects.get_or_create(user=self.request.user)
        context = super(AccountSettingsView, self).get_context_data(**kwargs)
        context.update({'title': "Settings", 'token': token})
        return context


class JiraLoginView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        consumer = oauth.Consumer(settings.OAUTH_CONSUMER_KEY, settings.OAUTH_CONSUMER_SECRET)
        client = oauth.Client(consumer)
        client.set_signature_method(SignatureMethod_RSA_SHA1())

        # Step 1. Get a request token from Jira.
        try:
            resp, content = client.request(settings.OAUTH_REQUEST_TOKEN_URL, "POST")
        except Exception:
            messages.add_message(self.request, messages.ERROR,
                                 'Error: Connection to Jira failed. Please contact an Administrator')
            return '/'
        if resp['status'] != '200':
            messages.add_message(self.request, messages.ERROR,
                                 'Error: Connection to Jira failed. Please contact an Administrator')
            return '/'

        # Step 2. Store the request token in a session for later use.
        self.request.session['request_token'] = dict(urllib.parse.parse_qsl(content.decode()))
        # Step 3. Redirect the user to the authentication URL.
        url = settings.OAUTH_AUTHORIZE_URL + '?oauth_token=' + \
            self.request.session['request_token']['oauth_token'] + \
            '&oauth_callback=' + settings.OAUTH_CALLBACK_URL
        return url


class JiraLogoutView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        logout(self.request)
        return '/'


class JiraAuthenticatedView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        # Step 1. Use the request token in the session to build a new client.
        consumer = oauth.Consumer(settings.OAUTH_CONSUMER_KEY, settings.OAUTH_CONSUMER_SECRET)
        token = oauth.Token(self.request.session['request_token']['oauth_token'],
                            self.request.session['request_token']['oauth_token_secret'])
        client = oauth.Client(consumer, token)
        client.set_signature_method(SignatureMethod_RSA_SHA1())

        # Step 2. Request the authorized access token from Jira.
        try:
            resp, content = client.request(settings.OAUTH_ACCESS_TOKEN_URL, "POST")
        except Exception:
            messages.add_message(self.request, messages.ERROR,
                                 'Error: Connection to Jira failed. Please contact an Administrator')
            return '/'
        if resp['status'] != '200':
            messages.add_message(self.request, messages.ERROR,
                                 'Error: Connection to Jira failed. Please contact an Administrator')
            return '/'

        access_token = dict(urllib.parse.parse_qsl(content.decode()))

        module_dir = os.path.dirname(__file__)  # get current directory
        with open(module_dir + '/rsa.pem', 'r') as f:
            key_cert = f.read()

        oauth_dict = {
            'access_token': access_token['oauth_token'],
            'access_token_secret': access_token['oauth_token_secret'],
            'consumer_key': settings.OAUTH_CONSUMER_KEY,
            'key_cert': key_cert
        }

        jira = JIRA(server=settings.JIRA_URL, oauth=oauth_dict)
        username = jira.current_user()
        email = jira.user(username).emailAddress
        url = '/'
        # Step 3. Lookup the user or create them if they don't exist.
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Save our permanent token and secret for later.
            user = User.objects.create_user(username=username,
                                            password=access_token['oauth_token_secret'])
            profile = UserProfile()
            profile.user = user
            profile.save()
            user.userprofile.email_addr = email
            url = reverse('account:settings')
        user.userprofile.oauth_token = access_token['oauth_token']
        user.userprofile.oauth_secret = access_token['oauth_token_secret']
        user.userprofile.save()
        user.set_password(access_token['oauth_token_secret'])
        user.save()
        user = authenticate(username=username, password=access_token['oauth_token_secret'])
        login(self.request, user)
        # redirect user to settings page to complete profile
        return url


@method_decorator(login_required, name='dispatch')
class UserListView(TemplateView):
    template_name = "account/user_list.html"

    def get_context_data(self, **kwargs):
        users = User.objects.all()
        context = super(UserListView, self).get_context_data(**kwargs)
        context.update({'title': "Dashboard Users", 'users': users})
        return context


def account_detail_view(request):
    template = "account/details.html"
    return render(request, template)


def account_resource_view(request):
    """
    gathers a users genericResoureBundles and
    turns them into displayable objects
    """
    if not request.user.is_authenticated:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})
    template = "account/resource_list.html"
    resources = GenericResourceBundle.objects.filter(
        owner=request.user).prefetch_related("configbundle_set")
    mapping = {}
    resource_list = []
    booking_mapping = {}
    for grb in resources:
        resource_list.append(grb)
        mapping[grb.id] = [{"id": x.id, "name": x.name} for x in grb.configbundle_set.all()]
        if Booking.objects.filter(resource__template=grb, end__gt=timezone.now()).exists():
            booking_mapping[grb.id] = "true"
    context = {
        "resources": resource_list,
        "grb_mapping": mapping,
        "booking_mapping": booking_mapping,
        "title": "My Resources"
    }
    return render(request, template, context=context)


def account_booking_view(request):
    if not request.user.is_authenticated:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})
    template = "account/booking_list.html"
    bookings = list(Booking.objects.filter(owner=request.user, end__gt=timezone.now()).order_by("-start"))
    my_old_bookings = Booking.objects.filter(owner=request.user, end__lt=timezone.now()).order_by("-start")
    collab_old_bookings = request.user.collaborators.filter(end__lt=timezone.now()).order_by("-start")
    expired_bookings = list(my_old_bookings.union(collab_old_bookings))
    collab_bookings = list(request.user.collaborators.filter(end__gt=timezone.now()).order_by("-start"))
    context = {
        "title": "My Bookings",
        "bookings": bookings,
        "collab_bookings": collab_bookings,
        "expired_bookings": expired_bookings
    }
    return render(request, template, context=context)


def account_configuration_view(request):
    if not request.user.is_authenticated:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})
    template = "account/configuration_list.html"
    configs = list(ConfigBundle.objects.filter(owner=request.user))
    context = {"title": "Configuration List", "configurations": configs}
    return render(request, template, context=context)


def account_images_view(request):
    if not request.user.is_authenticated:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})
    template = "account/image_list.html"
    my_images = Image.objects.filter(owner=request.user)
    public_images = Image.objects.filter(public=True)
    used_images = {}
    for image in my_images:
        if Host.objects.filter(booked=True, config__image=image).exists():
            used_images[image.id] = "true"
    context = {
        "title": "Images",
        "images": my_images,
        "public_images": public_images,
        "used_images": used_images
    }
    return render(request, template, context=context)


def resource_delete_view(request, resource_id=None):
    if not request.user.is_authenticated:
        return HttpResponse('no')  # 403?
    grb = get_object_or_404(GenericResourceBundle, pk=resource_id)
    if not request.user.id == grb.owner.id:
        return HttpResponse('no')  # 403?
    if Booking.objects.filter(resource__template=grb, end__gt=timezone.now()).exists():
        return HttpResponse('no')  # 403?
    grb.delete()
    return HttpResponse('')


def configuration_delete_view(request, config_id=None):
    if not request.user.is_authenticated:
        return HttpResponse('no')  # 403?
    config = get_object_or_404(ConfigBundle, pk=config_id)
    if not request.user.id == config.owner.id:
        return HttpResponse('no')  # 403?
    if Booking.objects.filter(config_bundle=config, end__gt=timezone.now()).exists():
        return HttpResponse('no')
    config.delete()
    return HttpResponse('')


def booking_cancel_view(request, booking_id=None):
    if not request.user.is_authenticated:
        return HttpResponse('no')  # 403?
    booking = get_object_or_404(Booking, pk=booking_id)
    if not request.user.id == booking.owner.id:
        return HttpResponse('no')  # 403?

    if booking.end < timezone.now():  # booking already over
        return HttpResponse('')

    booking.end = timezone.now()
    booking.save()
    return HttpResponse('')


def image_delete_view(request, image_id=None):
    if not request.user.is_authenticated:
        return HttpResponse('no')  # 403?
    image = get_object_or_404(Image, pk=image_id)
    if image.public or image.owner.id != request.user.id:
        return HttpResponse('no')  # 403?
    # check if used in booking
    if Host.objects.filter(booked=True, config__image=image).exists():
        return HttpResponse('no')  # 403?
    image.delete()
    return HttpResponse('')
