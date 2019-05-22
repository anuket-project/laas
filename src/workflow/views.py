##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.http import HttpResponse, HttpResponseGone
from django.shortcuts import render

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


def delete_session(request):
    manager = attempt_auth(request)

    if not manager:
        return HttpResponseGone("No session found that relates to current request")

    if manager.pop_workflow():
        return HttpResponse('')
    else:
        del ManagerTracker.managers[request.session['manager_session']]
        return render(request, 'workflow/exit_redirect.html')

    try:
        del ManagerTracker.managers[request.session['manager_session']]
        return HttpResponse('')
    except Exception:
        return None


def step_view(request):
    manager = attempt_auth(request)
    if not manager:
        # no manager found, redirect to "lost" page
        return no_workflow(request)
    if request.GET.get('step') is not None:
        if request.GET.get('step') == 'next':
            manager.go_next()
        elif request.GET.get('step') == 'prev':
            manager.go_prev()
        else:
            raise Exception("requested action for new step had malformed contents: " + request.GET.get('step'))
    return manager.render(request)


def manager_view(request):
    manager = attempt_auth(request)

    if not manager:
        return HttpResponseGone("No session found that relates to current request")

    if request.method == 'GET':
        # no need for this statement if only intercepting post requests

        # return general context for viewport page
        return manager.status(request)

    if request.method == 'POST':
        if request.POST.get('add') is not None:
            logger.debug("add found")
            target_id = None
            if 'target' in request.POST:
                target_id = int(request.POST.get('target'))
            manager.add_workflow(workflow_type=int(request.POST.get('add')), target_id=target_id)
        elif request.POST.get('edit') is not None and request.POST.get('edit_id') is not None:
            logger.debug("edit found")
            manager.add_workflow(workflow_type=request.POST.get('edit'), edit_object=int(request.POST.get('edit_id')))
        elif request.POST.get('cancel') is not None:
            if not manager.pop_workflow():
                del ManagerTracker.managers[request.session['manager_session']]

    return manager.status(request)


def viewport_view(request):
    if not request.user.is_authenticated:
        return login(request)

    manager = attempt_auth(request)
    if manager is None:
        return no_workflow(request)

    if request.method == 'GET':
        return render(request, 'workflow/viewport-base.html')
    else:
        pass


def create_session(wf_type, request):
    wf = int(wf_type)
    smgr = SessionManager(request=request)
    smgr.add_workflow(workflow_type=wf, target_id=request.POST.get("target"))
    manager_uuid = uuid.uuid4().hex
    ManagerTracker.getInstance().managers[manager_uuid] = smgr

    return manager_uuid


def no_workflow(request):

    logger.debug("There is no active workflow")

    return render(request, 'workflow/no_workflow.html', {'title': "Not Found"})


def login(request):
    return render(request, "dashboard/login.html", {'title': 'Authentication Required'})
