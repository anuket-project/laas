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
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import RedirectView, TemplateView, UpdateView
from django.shortcuts import render
from api.utils import ipa_set_ssh, ipa_query_user, ipa_set_company
from dashboard.forms import SetCompanyForm, SetSSHForm
from rest_framework.authtoken.models import Token
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


from account.forms import AccountPreferencesForm
from account.models import UserProfile
from booking.models import Booking
from api.views import delete_template, liblaas_templates
from workflow.views import login

def account_settings_view(request):
    if request.method == "GET":
        if not request.user.is_authenticated:
            return login(request)
        profile = UserProfile.objects.get(user=request.user)
        if (not profile or profile.ipa_username == "" or profile.ipa_username == None):
            return redirect("dashboard:index")
        ipa_user = ipa_query_user(profile.ipa_username)
        template = "account/settings.html"
        context = {
            "preference_form": AccountPreferencesForm(instance=profile),
            "company_form": SetCompanyForm(initial={'company': ipa_user['ou']}),
            "existing_keys": ipa_user['ipasshpubkey'] if 'ipasshpubkey' in ipa_user else []
        }
        return render(request, template, context)       

    if request.method == 'POST':
        data = request.POST

        print("data is", data)
        # User profile
        profile = UserProfile.objects.get(user=request.user)
        profile.public_user = "public_user" in data
        profile.timezone = data["timezone"]
        profile.save()

        # IPA
        ipa_set_company(profile, data['company'])
        ipa_set_ssh(profile, data['ssh_key_list'].split(","))

        return redirect("account:settings")

    return HttpResponse(status=405)

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
        profile = UserProfile.objects.get(user=request.user)
        if (not profile or profile.ipa_username == "" or profile.ipa_username == None):
            return redirect("dashboard:index")
        r = liblaas_templates(request)
        usable_templates = r.json()
        user_templates = [ t for t in usable_templates if t["owner"] == profile.ipa_username]
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
    profile = UserProfile.objects.get(user=request.user)
    if (not profile or profile.ipa_username == "" or profile.ipa_username == None):
        return redirect("dashboard:index")
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

