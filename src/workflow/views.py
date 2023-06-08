##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

import json
from django.shortcuts import render
from laas_dashboard.settings import TEMPLATE_OVERRIDE
from django.http import HttpResponse
from django.http.response import JsonResponse
from workflow.forms import BookingMetaForm
from api.views import liblaas_request, make_booking


def no_workflow(request):
    return render(request, 'workflow/no_workflow.html', {'title': "Not Found"}, status=404)


def login(request):
    return render(request, "dashboard/login.html", {'title': 'Authentication Required'})

def design_a_pod_view(request):
    if request.method == "GET":
        if not request.user.is_authenticated:
            return login(request)
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
        template = "workflow/book_a_pod.html"
        context = {
            "dashboard": str(TEMPLATE_OVERRIDE),
            "form": BookingMetaForm(initial={}, user_initial=[], owner=request.user),
        }
        return render(request, template, context)
    
    if request.method == "POST":
        print("forwarding request to liblaas...")
        return liblaas_request(request)

    # Using PUT to signal that we do not want to talk to liblaas
    if request.method == "PUT":
        return make_booking(request)

    return HttpResponse(status=405)
