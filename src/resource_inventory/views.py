##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

import json
import os
from django.shortcuts import render
from django.http import HttpResponse
from laas_dashboard.settings import PROJECT

from liblaas.views import flavor_list_hosts, flavor_list_flavors

def host_list_view(request):
    if request.method != "GET":
        return HttpResponse(status=405)

    host_list = flavor_list_hosts(PROJECT)
    flavor_list = flavor_list_flavors(PROJECT)

    flavor_map = {}
    for flavor in flavor_list:
        flavor_map[flavor['flavor_id']] = flavor['name']

    # Apparently Django Templating lacks many features that regular Jinja offers, so I need to get creative
    for host in host_list:
        id = host["flavor"]
        name = flavor_map[id]
        host["flavor"] = {"id": id, "name": name}

    template = "resource/hosts.html"
    context = {
        "hosts": host_list,
        "flavor_map": flavor_map
    }
    return render(request, template, context)



def profile_view(request, resource_id):
    if request.method != "GET":
        return HttpResponse(status=405)

    flavor_list = flavor_list_flavors(PROJECT)
    selected_flavor = {}
    for flavor in flavor_list:
        if flavor["flavor_id"] == resource_id:
            selected_flavor = flavor
            break

    template = "resource/hostprofile_detail.html"
    context = {
        "flavor": selected_flavor
    }
    return render(request, template, context)
