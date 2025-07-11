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
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.shortcuts import render
from django.db.models import Q
from django.template import RequestContext
from datetime import datetime
import pytz
from django.http import HttpResponse

from account.models import Lab, UserProfile
from booking.models import Booking
from laas_dashboard import settings
from laas_dashboard.settings import PROJECT, SITE_CONTACT
from liblaas.utils import get_ipa_status

from liblaas.views import flavor_list_flavors, flavor_list_hosts


def lab_list_view(request):
    labs = Lab.objects.all().order_by("name")
    

    flavors_list = flavor_list_flavors(PROJECT)
    host_list = flavor_list_hosts(PROJECT)

    # Make sure each host.flavor value has its id (for a link) and name
        # Done in view instead of template since Django templating is limited and to reduce the amount of unnecessary values passed by context
    flavor_map = {}
    for flavor in flavors_list:
        flavor_map[flavor['flavor_id']] = flavor['name']

    for host in host_list:
        id = host["flavor"]
        name = flavor_map[id]
        host["flavor"] = {"id": id, "name": name}
 

    context = {
        'labs': labs,
        'hosts': host_list,
        'title': 'Labs'
    }

    return render(request, "dashboard/lab_list.html", context)


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
    ipa_status = "n/a"
    profile = {}
    
    if not user.is_anonymous:
        bookings = Booking.objects.filter(
            Q(owner=user) | Q(collaborators=user), end__gte=datetime.now(pytz.utc)
        ).distinct()

        # new, link, conflict, n/a
        ipa_status = get_ipa_status(user)
        up = UserProfile.objects.get(user=user)
        profile["email"] = up.email_addr

        # Link by default, no need for modal
        if ipa_status == "link":
            up.ipa_username = str(user)
            up.save()
    else:
        bookings = None

    LFID = True if settings.AUTH_SETTING == 'LFID' else False
    dev_login = True if settings.AUTH_SETTING == 'DEV_NORMAL' else False

    if request.method != "GET":
        return HttpResponse(status_code=405)

    return render(
        request,
        'dashboard/landing.html',
        {
            'title': "Welcome to the Lab as a Service Dashboard",
            'bookings': bookings,
            'LFID': LFID,
            'dev_login': dev_login,
            'ipa_status': ipa_status,
        }
    )

def handler404(request, exception):
    response = render(request, "dashboard/404.html")
    response.status_code = 404
    return response


def handler500(request):
    context = {
        "contact": SITE_CONTACT
    }
    response = render(request, "dashboard/500.html", context)
    response.status_code = 500
    return response

class LandingView(TemplateView):
    template_name = "dashboard/landing.html"

    def get_context_data(self, **kwargs):
        context = super(LandingView, self).get_context_data(**kwargs)

        return context
