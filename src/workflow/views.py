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
from liblaas.views import user_get_user
from workflow.forms import BookingMetaForm
from account.models import UserProfile


def login(request):
    return render(request, "dashboard/login.html", {'title': 'Authentication Required'})

def design_a_pod_view(request):
    if request.method != "GET":
        return HttpResponse(status=405)

    if not request.user.is_authenticated:
        return login(request)

    profile = UserProfile.objects.get(user=request.user)

    if (not profile or profile.ipa_username == None):
        return redirect("dashboard:index")

    template = "workflow/design_a_pod.html"
    context = {
        "dashboard": str(TEMPLATE_OVERRIDE)
    }
    return render(request, template, context)


def book_a_pod_view(request):
    if request.method != "GET":
        return HttpResponse(status=405)

    if not request.user.is_authenticated:
        return login(request)

    profile = UserProfile.objects.get(user=request.user)

    if (not profile or profile.ipa_username == None):
        return redirect("dashboard:index")

    vpn_user = user_get_user(profile.ipa_username)
    
    # These booleans need to be represented as strings, due to the way jinja interprets them
    prereqs = {
        "company": "true" if ("ou" in vpn_user and vpn_user["ou"] != "") else "false",
        "keys": "true" if ("ipasshpubkey" in vpn_user) and (len(vpn_user["ipasshpubkey"]) > 0) else "false"
    }

    template = "workflow/book_a_pod.html"
    context = {
        "dashboard": str(TEMPLATE_OVERRIDE),
        "form": BookingMetaForm(initial={}, user_initial=[], owner=request.user),
        "prereqs": prereqs
    }
    return render(request, template, context)


