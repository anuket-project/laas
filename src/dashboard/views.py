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
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.shortcuts import render
from django.db.models import Q
from datetime import datetime
import pytz

from account.models import Lab, UserProfile
from api.utils import get_ipa_migration_form, ipa_query_user
from api.views import ipa_conflict_account
from booking.models import Booking
from dashboard.forms import *
from api.views import list_flavors, list_hosts

from laas_dashboard import settings


def lab_list_view(request):
    labs = Lab.objects.all()
    context = {"labs": labs, 'title': 'Labs'}

    return render(request, "dashboard/lab_list.html", context)


def lab_detail_view(request, lab_name):
    # todo - LL Integration
    user = None
    if request.user.is_authenticated:
        user = request.user

    lab = get_object_or_404(Lab, name=lab_name)
    flavors_list = json.loads(list_flavors(request).content)
    host_list = json.loads(list_hosts(request).content)
    flavor_map = {}
    for flavor in flavors_list:
        flavor_map[flavor['flavor_id']] = flavor['name']
        

    # Apparently Django Templating lacks many features that regular Jinja offers, so I need to get creative
    for host in host_list:
        id = host["flavor"]
        name = flavor_map[id]
        host["flavor"] = {"id": id, "name": name}

    return render(
        request,
        "dashboard/lab_detail.html",
        {
            'title': "Lab Overview",
            'lab': lab,
            # 'hostprofiles': ResourceProfile.objects.filter(labs=lab),
            'flavors': flavors_list,
            'hosts': host_list
        }
    )


def host_profile_detail_view(request):

    return render(
        request,
        "dashboard/host_profile_detail.html",
        {
            'title': "Host Types",
        }
    )


def landing_view(request):
    user = request.user
    ipa_migrator = {
        "exists": "false" # Jinja moment
    }
    if not user.is_anonymous:
        bookings = Booking.objects.filter(
            Q(owner=user) | Q(collaborators=user),
            end__gte=datetime.now(pytz.utc)
        )
        profile = UserProfile.objects.get(user=user)
        if (not profile.ipa_username):
             ipa_migrator = get_ipa_migration_form(user, profile)
             ipa_migrator["exists"] = "true"

    else:
        bookings = None

    print("IPA migrator is", ipa_migrator)
    LFID = True if settings.AUTH_SETTING == 'LFID' else False

    if request.method == "GET":
        return render(
            request,
            'dashboard/landing.html',
            {
                'title': "Welcome to the Lab as a Service Dashboard",
                'bookings': bookings,
                'LFID': LFID,
                'ipa_migrator': ipa_migrator,
            }
        )
    
    # Using this for the special case in the ipa_migrator
    if request.method == 'POST':
        existing_profile = ipa_query_user(request.POST['ipa_username'])
        print("exists already?", existing_profile != None)
        if (existing_profile != None):
            return render(
                request,
                'dashboard/landing.html',
                {
                    'title': "Welcome to the Lab as a Service Dashboard",
                    'bookings': bookings,
                    'LFID': LFID,
                    'ipa_migrator': ipa_migrator,
                    'error': "Username is already taken"
                }
            )
        else:
            return ipa_conflict_account(request)

class LandingView(TemplateView):
    template_name = "dashboard/landing.html"

    def get_context_data(self, **kwargs):
        context = super(LandingView, self).get_context_data(**kwargs)

        return context
