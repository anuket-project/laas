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
from django.http import HttpResponseRedirect

from account.models import Lab

from resource_inventory.models import Image, HostProfile
from workflow.views import create_session
from workflow.workflow_manager import ManagerTracker


def lab_list_view(request):
    labs = Lab.objects.all()
    context = {"labs": labs}

    return render(request, "dashboard/lab_list.html", context)


def lab_detail_view(request, lab_name):
    user = None
    if request.user.is_authenticated:
        user = request.user

    lab = get_object_or_404(Lab, name=lab_name)

    images = Image.objects.filter(from_lab=lab).filter(public=True)
    if user:
        images = images | Image.objects.filter(from_lab=lab).filter(owner=user)

    return render(
        request,
        "dashboard/lab_detail.html",
        {
            'title': "Lab Overview",
            'lab': lab,
            'hostprofiles': lab.hostprofiles.all(),
            'images': images
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
    manager = None
    manager_detected = False
    if 'manager_session' in request.session:

        try:
            manager = ManagerTracker.managers[request.session['manager_session']]

        except KeyError:
            pass

    if manager is not None:
        # no manager detected, don't display continue button
        manager_detected = True

    if request.method == 'GET':
        return render(request, 'dashboard/landing.html', {'manager': manager_detected, 'title': "Welcome!"})

    if request.method == 'POST':
        try:
            create = request.POST['create']

            if manager is not None:
                del manager

            mgr_uuid = create_session(create, request=request,)
            request.session['manager_session'] = mgr_uuid
            return HttpResponseRedirect('/wf/')

        except KeyError:
            pass


class LandingView(TemplateView):
    template_name = "dashboard/landing.html"

    def get_context_data(self, **kwargs):
        context = super(LandingView, self).get_context_data(**kwargs)

        hosts = []

        for host_profile in HostProfile.objects.all():
            name = host_profile.name
            description = host_profile.description
            in_labs = host_profile.labs

            interfaces = host_profile.interfaceprofile
            storage = host_profile.storageprofile
            cpu = host_profile.cpuprofile
            ram = host_profile.ramprofile

            host = (name, description, in_labs, interfaces, storage, cpu, ram)
            hosts.append(host)

        context.update({'hosts': hosts})

        return context
