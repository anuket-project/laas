##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


import json
import os

from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import RedirectView, TemplateView, UpdateView
from django.shortcuts import render
from rest_framework.authtoken.models import Token
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


from account.forms import AccountSettingsForm
from account.models import UserProfile
from booking.models import Booking
from api.views import delete_template, liblaas_templates
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


class MyOIDCAB(OIDCAuthenticationBackend):
    def filter_users_by_claims(self, claims):
        """
        Checks to see if user exists and create user if not

        Linux foundation does not allow users to change their
        username, so chose to match users based on their username.
        If this changes we will need to match users based on some
        other criterea.
        """
        username = claims.get(os.environ.get('CLAIMS_ENDPOINT') + 'username')

        if not username:
            return HttpResponse('No username provided, contact support.')

        try:
            # For literally no (good) reason user needs to be a queryset
            user = User.objects.filter(username=username)
            return user
        except User.DoesNotExist:
            return self.UserModel.objects.none()

    def create_user(self, claims):
        """ This creates a user and user profile"""
        user = super(MyOIDCAB, self).create_user(claims)
        user.username = claims.get(os.environ['CLAIMS_ENDPOINT'] + 'username')
        user.save()

        up = UserProfile()
        up.user = user
        up.email_addr = claims.get('email')
        up.save()
        return user

    def update_user(self, user, claims):
        """ If their account has different email, change the email """
        up = UserProfile.objects.get(user=user)
        up.email_addr = claims.get('email')
        up.save()
        return user


class OIDCLoginView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        return reverse('oidc_authentication_init')


class LogoutView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        logout(self.request)
        return '/'


@method_decorator(login_required, name='dispatch')
class UserListView(TemplateView):
    template_name = "account/user_list.html"

    def get_context_data(self, **kwargs):
        users = UserProfile.objects.filter(public_user=True).select_related('user')
        context = super(UserListView, self).get_context_data(**kwargs)
        context.update({'title': "Dashboard Users", 'users': users})
        return context


def account_detail_view(request):
    template = "account/details.html"
    return render(request, template)


def account_resource_view(request):
    """
    Display a user's resources.

    gathers a users genericResoureBundles and
    turns them into displayable objects
    """
    if not request.user.is_authenticated:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})
    template = "account/resource_list.html"

    if request.method == "GET":

        r = liblaas_templates(request)
        usable_templates = r.json()
        user_templates = [ t for t in usable_templates if t["owner"] == str(request.user)]
        context = {
            "templates": user_templates,
            "title": "My Resources"
        }
        return render(request, template, context=context)
    
    if request.method == "POST":
        return delete_template(request)
    
    return HttpResponse(status_code=405)


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



def template_delete_view(request, resource_id=None):
    # if not request.user.is_authenticated:
    #     return HttpResponse(status=403)
    # template = get_object_or_404(ResourceTemplate, pk=resource_id)
    # if not request.user.id == template.owner.id:
    #     return HttpResponse(status=403)
    # if Booking.objects.filter(resource__template=template, end__gt=timezone.now()).exists():
    #     return HttpResponse(status=403)
    # template.public = False
    # template.temporary = True
    # template.save()
    # return HttpResponse(status=200)
    return HttpResponse(status=404) # todo - LL Integration


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

