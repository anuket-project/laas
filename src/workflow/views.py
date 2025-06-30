##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.shortcuts import render, redirect
from laas_dashboard.settings import PROJECT, SUB_PROJECTS
from django.http import HttpResponse, HttpRequest
from liblaas.views import user_get_user
from workflow.forms import BookingMetaForm
from account.models import UserProfile
from liblaas.views import template_list_templates


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

    if user_get_user(profile.ipa_username) is None:
        raise Exception("Unable to query user from IPA")

    constraints = get_workflow_contraints(PROJECT)
    template = "workflow/design_a_pod.html"
    context = {
        "constraints": constraints,
        "project": PROJECT
    }
    return render(request, template, context)


def book_a_pod_view(request: HttpRequest):
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

    
    template_list = template_list_templates(request.user.userprofile.ipa_username, PROJECT)
    
    if not template_list:
        return HttpResponse(status=500)
    
    # Separate the given templates into whether or not the user owns them in order to differentiate in the html template
    templates = {
        "public" : [], 
        "private" : [],
        "display_size": 0,
    }

    for template in template_list:
        if template.get("owner") == request.user.userprofile.ipa_username:
            templates["private"].append(template)
        else:
            templates["public"].append(template)

    templates["public"].sort(key=lambda template : template["id"])
    templates["private"].sort(key=lambda template : template["id"])
    templates["display_size"] = min(10, max(len(templates["public"]), len(templates["private"])) + 4)

    template = "workflow/book_a_pod.html"
    context = {
        "form": BookingMetaForm(initial={}, user_initial=[], owner=request.user),
        "prereqs": prereqs,
        "project": PROJECT,
        "sub_projects" : SUB_PROJECTS,
        "purposes" : ["CI/CD", "Testing", "Training", "Demo", "Development", "Other"],
        "templates" : templates,
    }
    return render(request, template, context)

def get_workflow_contraints(project: str) -> dict:

    if project == 'anuket':
        return {
            "max_hosts": 8,
        }

    if project == 'lfedge':
        return {
            "max_hosts": "null",
        }

    return {}


