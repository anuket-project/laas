##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views import View
from django.http.response import JsonResponse, HttpResponse
from rest_framework.authtoken.models import Token
from django.views.decorators.csrf import csrf_exempt

from api.forms import DowntimeForm
from account.models import UserProfile, Lab
from booking.models import Booking
from api.models import LabManagerTracker,AutomationAPIManager, APILog

"""
API views.

All functions return a Json blob
Most functions that deal with info from a specific lab (tasks, host info)
requires the Lab auth token.
    for example, curl -H auth-token:mylabsauthtoken url

Most functions let you GET or POST to the same endpoint, and
the correct thing will happen
"""

@method_decorator(login_required, name='dispatch')
class GenerateTokenView(View):
    def get(self, request, *args, **kwargs):
        user = self.request.user
        token, created = Token.objects.get_or_create(user=user)
        if not created:
            token.delete()
            Token.objects.create(user=user)
        return redirect('account:settings')


def lab_status(request, lab_name=""):
    lab_token = request.headers.get('auth-token')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    if request.method == "POST":
        return JsonResponse(lab_manager.set_status(request.POST), safe=False)
    return JsonResponse(lab_manager.get_status(), safe=False)


def lab_users(request, lab_name=""):
    lab_token = request.headers.get('auth-token')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    return HttpResponse(lab_manager.get_users(), content_type="text/plain")


def lab_user(request, lab_name="", user_id=-1):
    lab_token = request.headers.get('auth-token')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    return HttpResponse(lab_manager.get_user(user_id), content_type="text/plain")


def lab_profile(request, lab_name=""):
    lab_token = request.headers.get('auth-token')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    return JsonResponse(lab_manager.get_profile(), safe=False)



def lab_downtime(request, lab_name=""):
    lab_token = request.headers.get('auth-token')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    if request.method == "GET":
        return JsonResponse(lab_manager.get_downtime_json())
    if request.method == "POST":
        return post_lab_downtime(request, lab_manager)
    if request.method == "DELETE":
        return delete_lab_downtime(lab_manager)
    return HttpResponse(status=405)


def post_lab_downtime(request, lab_manager):
    current_downtime = lab_manager.get_downtime()
    if current_downtime.exists():
        return JsonResponse({"error": "Lab is already in downtime"}, status=422)
    form = DowntimeForm(request.POST)
    if form.is_valid():
        return JsonResponse(lab_manager.create_downtime(form))
    else:
        return JsonResponse(form.errors.get_json_data(), status=400)


def delete_lab_downtime(lab_manager):
    current_downtime = lab_manager.get_downtime()
    if current_downtime.exists():
        dt = current_downtime.first()
        dt.end = timezone.now()
        dt.save()
        return JsonResponse(lab_manager.get_downtime_json(), safe=False)
    else:
        return JsonResponse({"error": "Lab is not in downtime"}, status=422)


def auth_and_log(request, endpoint):
    """
    Function to authenticate an API user and log info
    in the API log model. This is to keep record of
    all calls to the dashboard
    """
    user_token = request.headers.get('auth-token')
    response = None

    if user_token is None:
        return HttpResponse('Unauthorized', status=401)

    try:
        token = Token.objects.get(key=user_token)
    except Token.DoesNotExist:
        token = None
        if len(str(user_token)) != 40:
            response = HttpResponse('Malformed Token', status=401)
        else:
            response = HttpResponse('Unauthorized', status=401)

    x_forwarded_for = request.headers.get('x-forwarded-for')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    body = None

    if request.method in ['POST', 'PUT']:
        try:
            body = json.loads(request.body.decode('utf-8')),
        except Exception:
            response = HttpResponse('Invalid Request Body', status=400)

    APILog.objects.create(
        user=token.user,
        call_time=timezone.now(),
        method=request.method,
        endpoint=endpoint,
        body=body,
        ip_addr=ip
    )

    if response:
        return response
    else:
        return token


"""
User API Views
"""


def all_users(request):
    token = auth_and_log(request, 'users')

    if token is None:
        return HttpResponse('Unauthorized', status=401)

    users = [AutomationAPIManager.serialize_userprofile(up)
             for up in UserProfile.objects.filter(public_user=True)]

    return JsonResponse(users, safe=False)


"""
Lab API Views
"""


def list_labs(request):
    lab_list = []
    for lab in Lab.objects.all():
        lab_info = {
            'name': lab.name,
            'username': lab.lab_user.username,
            'status': lab.status,
            'project': lab.project,
            'description': lab.description,
            'location': lab.location,
            'info': lab.lab_info_link,
            'email': lab.contact_email,
            'phone': lab.contact_phone
        }
        lab_list.append(lab_info)

    return JsonResponse(lab_list, safe=False)

