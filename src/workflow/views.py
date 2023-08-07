##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

import json
from django.shortcuts import render, redirect
from laas_dashboard.settings import TEMPLATE_OVERRIDE
from django.http import HttpResponse
from django.http.response import JsonResponse
from workflow.forms import BookingMetaForm
from api.views import liblaas_request, make_booking
from api.utils import  get_booking_prereqs_validator
from account.models import UserProfile


def no_workflow(request):
    return render(request, 'workflow/no_workflow.html', {'title': "Not Found"}, status=404)


def login(request):
    return render(request, "dashboard/login.html", {'title': 'Authentication Required'})

def design_a_pod_view(request):
    if request.method == "GET":
        if not request.user.is_authenticated:
            return login(request)
        prereq_validator = get_booking_prereqs_validator(UserProfile.objects.get(user=request.user))
        if (prereq_validator["action"] == "no user"):
            return redirect("dashboard:index")
        template = "workflow/design_a_pod.html"
        context = {
            "dashboard": str(TEMPLATE_OVERRIDE)
        }
        return render(request, template, context)
    
    if request.method == "POST":
        print("forwarding request to liblaas...")
        return liblaas_request(request)

    return HttpResponse(status=405)

def book_a_pod_view(request):
    if request.method == "GET":
        if not request.user.is_authenticated:
            return login(request)
        prereq_validator = get_booking_prereqs_validator(UserProfile.objects.get(user=request.user))
        if (prereq_validator["action"] == "no user"):
            return redirect("dashboard:index")
        template = "workflow/book_a_pod.html"
        context = {
            "dashboard": str(TEMPLATE_OVERRIDE),
            "form": BookingMetaForm(initial={}, user_initial=[], owner=request.user),
            "prereq_validator": prereq_validator
        }
        return render(request, template, context)
    
    if request.method == "POST":
        print("forwarding request to liblaas...")
        return liblaas_request(request)

    # Using PUT to signal that we do not want to talk to liblaas
    if request.method == "PUT":
        return make_booking(request)

    return HttpResponse(status=405)
