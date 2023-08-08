##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

import json
from django.shortcuts import render
from django.http import HttpResponse
from api.views import list_hosts, list_flavors


def host_list_view(request):
    if request.method == "GET":
        host_list = json.loads(list_hosts(request).content)
        flavor_list = json.loads(list_flavors(request).content)
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

    return HttpResponse(status=405)


def profile_view(request, resource_id):
    if request.method == "GET":
        flavor_list = json.loads(list_flavors(request).content)
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

    return HttpResponse(status=405)