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
import pytz
import json
from django.utils import timezone
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.generic import RedirectView
from django.shortcuts import render
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from account.models import UserProfile
from booking.models import Booking
from workflow.views import login

from liblaas.views import user_get_user,user_set_company, user_set_ssh, \
template_list_templates, template_delete_template, booking_end_booking

def account_settings_view(request):
    if request.method == "GET":
        if not request.user.is_authenticated:
            return login(request)

        profile = UserProfile.objects.get(user=request.user)

        ipa_user = user_get_user(profile.ipa_username)
        template = "account/settings.html"

        context = {
            "timezone": profile.timezone,
            "timezones": [(x) for x in pytz.common_timezones],
            "public": profile.public_user,
            "company": ipa_user["ou"] if 'ou' in ipa_user else "",
            "existing_keys": ipa_user['ipasshpubkey'] if 'ipasshpubkey' in ipa_user else [],
            "ipa_username": profile.ipa_username
        }

        return render(request, template, context)

    if request.method == "POST":
        return account_update_settings(request)
    
    return HttpResponse(status=405)

def account_update_settings(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    data = json.loads(request.body.decode('utf-8'))
    profile = UserProfile.objects.get(user=request.user)
    profile.public_user = data["public_user"]

    if data["timezone"] in pytz.common_timezones:
        profile.timezone = data["timezone"]
    r1 = user_set_company(profile.ipa_username, data["company"])
    r2 = user_set_ssh(profile, data["keys"])

    if (r1 and r2):
        profile.save()
        return HttpResponse(status=200)


    return HttpResponse(status=500)

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
    """

    if request.method == "GET":

        if not request.user.is_authenticated:
            return render(request, "dashboard/login.html", {'title': 'Authentication Required'})
        template = "account/resource_list.html"

        profile = UserProfile.objects.get(user=request.user)
        if (not profile or profile.ipa_username == None):
            return redirect("dashboard:index")

        usable_templates = template_list_templates(profile.ipa_username)
        user_templates = [ t for t in usable_templates if t["owner"] == profile.ipa_username]
        context = {
            "templates": user_templates,
            "title": "My Resources"
        }
        return render(request, template, context=context)

    if request.method == "POST":
        return account_delete_resource(request)

    return HttpResponse(status_code=405)


def account_delete_resource(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    data = json.loads(request.body.decode('utf-8'))
    template_id = data["template_id"]

    if not canDeleteTemplate(template_id, UserProfile.objects.get(user=request.user).ipa_username):
        return HttpResponse(status=401)

    response = template_delete_template(template_id)
    if (response):
        return HttpResponse(status=200)


    return HttpResponse(status=500)

def canDeleteTemplate(template_id, ipa_username):
    usable_templates = template_list_templates(ipa_username)
    for t in usable_templates:
        if (t['id'] == template_id and t['owner'] == ipa_username):
            return True

    return False

def account_booking_view(request):
    if request.method == 'GET':
        if not request.user.is_authenticated:
            return render(request, "dashboard/login.html", {'title': 'Authentication Required'})

        profile = UserProfile.objects.get(user=request.user)
        if (not profile or profile.ipa_username == None):
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

    if request.method == 'POST':
        return account_cancel_booking(request)

    return HttpResponse(status=405)

def account_cancel_booking(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    data = json.loads(request.body.decode('utf-8'))
    booking_id = data["booking_id"]
    booking = Booking.objects.get(id=booking_id)
    if not (booking.owner == request.user):
        return HttpResponse(401)

    # LibLaaS
    response = booking_end_booking(booking.aggregateId)

    # Dashboard
    booking.end = timezone.now()
    booking.save()

    if (response):
        return HttpResponse(status=200)

    return HttpResponse(status=500)


