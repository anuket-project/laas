##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.shortcuts import render
from django.db.models import Q
from datetime import datetime
import pytz

from account.models import Lab
from booking.models import Booking


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

    # images = Image.objects.filter(from_lab=lab).filter(public=True)
    images = []
    # if user:
    #     images = images | Image.objects.filter(from_lab=lab).filter(owner=user)

    # hosts = ResourceQuery.filter(lab=lab)
    hosts = []

    return render(
        request,
        "dashboard/lab_detail.html",
        {
            'title': "Lab Overview",
            'lab': lab,
            # 'hostprofiles': ResourceProfile.objects.filter(labs=lab),
            'images': images,
            'hosts': hosts
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
    if not user.is_anonymous:
        bookings = Booking.objects.filter(
            Q(owner=user) | Q(collaborators=user),
            end__gte=datetime.now(pytz.utc)
        )
    else:
        bookings = None

    LFID = True if settings.AUTH_SETTING == 'LFID' else False
    return render(
        request,
        'dashboard/landing.html',
        {
            'title': "Welcome to the Lab as a Service Dashboard",
            'bookings': bookings,
            'LFID': LFID
        }
    )


class LandingView(TemplateView):
    template_name = "dashboard/landing.html"

    def get_context_data(self, **kwargs):
        context = super(LandingView, self).get_context_data(**kwargs)

        return context
