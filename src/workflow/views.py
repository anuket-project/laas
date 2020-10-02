##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.http import HttpResponse
from django.shortcuts import render
from account.models import Lab

import uuid

from workflow.workflow_manager import ManagerTracker, SessionManager

import logging
logger = logging.getLogger(__name__)


def attempt_auth(request):
    try:
        manager = ManagerTracker.managers[request.session['manager_session']]

        return manager

    except KeyError:
        return None


def remove_workflow(request):
    manager = attempt_auth(request)

    if not manager:
        return no_workflow(request)

    has_more_workflows, result = manager.pop_workflow(discard=True)

    if not has_more_workflows:  # this was the last workflow, so delete the reference to it in the tracker
        del ManagerTracker.managers[request.session['manager_session']]
    return manager.render(request)


def add_workflow(request):
    manager = attempt_auth(request)
    if not manager:
        return no_workflow(request)
    try:
        workflow_type = int(request.POST.get('workflow_type'))
    except ValueError:
        return HttpResponse(status=400)

    manager.add_workflow(workflow_type=workflow_type)
    return manager.render(request)  # do we want this?


def manager_view(request):
    manager = attempt_auth(request)
    if not manager:
        return no_workflow(request)

    return manager.handle_request(request)


def viewport_view(request):
    if not request.user.is_authenticated:
        return login(request)

    manager = attempt_auth(request)
    if manager is None:
        return no_workflow(request)

    if request.method != 'GET':
        return HttpResponse(status=405)

    context = {
        'contact_email': Lab.objects.get(name="UNH_IOL").contact_email
    }

    return render(request, 'workflow/viewport-base.html', context)


def create_workflow(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    workflow_type = request.POST.get('workflow_type')
    try:
        workflow_type = int(workflow_type)
    except Exception:
        return HttpResponse(status=400)
    mgr_uuid = create_session(workflow_type, request=request,)
    request.session['manager_session'] = mgr_uuid
    return HttpResponse()


def create_session(wf_type, request):
    smgr = SessionManager(request=request)
    smgr.add_workflow(workflow_type=wf_type, target_id=request.POST.get("target"))
    manager_uuid = uuid.uuid4().hex
    ManagerTracker.getInstance().managers[manager_uuid] = smgr

    return manager_uuid


def no_workflow(request):
    return render(request, 'workflow/no_workflow.html', {'title': "Not Found"}, status=404)


def login(request):
    return render(request, "dashboard/login.html", {'title': 'Authentication Required'})
