##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views import View
from django.http.response import JsonResponse, HttpResponse
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from django.views.decorators.csrf import csrf_exempt

from api.serializers.booking_serializer import BookingSerializer
from api.serializers.old_serializers import UserSerializer
from api.forms import DowntimeForm
from account.models import UserProfile
from booking.models import Booking
from api.models import LabManagerTracker, get_task
from notifier.manager import NotificationHandler

"""
API views.

All functions return a Json blob
Most functions that deal with info from a specific lab (tasks, host info)
requires the Lab auth token.
    for example, curl -H auth-token:mylabsauthtoken url

Most functions let you GET or POST to the same endpoint, and
the correct thing will happen
"""


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    filter_fields = ('resource', 'id')


class UserViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserSerializer


@method_decorator(login_required, name='dispatch')
class GenerateTokenView(View):
    def get(self, request, *args, **kwargs):
        user = self.request.user
        token, created = Token.objects.get_or_create(user=user)
        if not created:
            token.delete()
            Token.objects.create(user=user)
        return redirect('account:settings')


def lab_inventory(request, lab_name=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    return JsonResponse(lab_manager.get_inventory(), safe=False)


@csrf_exempt
def lab_host(request, lab_name="", host_id=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    if request.method == "GET":
        return JsonResponse(lab_manager.get_host(host_id), safe=False)
    if request.method == "POST":
        return JsonResponse(lab_manager.update_host(host_id, request.POST), safe=False)


def get_pdf(request, lab_name="", booking_id=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    return HttpResponse(lab_manager.get_pdf(booking_id), content_type="text/plain")


def get_idf(request, lab_name="", booking_id=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    return HttpResponse(lab_manager.get_idf(booking_id), content_type="text/plain")


def lab_status(request, lab_name=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    if request.method == "POST":
        return JsonResponse(lab_manager.set_status(request.POST), safe=False)
    return JsonResponse(lab_manager.get_status(), safe=False)


def lab_users(request, lab_name=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    return HttpResponse(lab_manager.get_users(), content_type="text/plain")


def lab_user(request, lab_name="", user_id=-1):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    return HttpResponse(lab_manager.get_user(user_id), content_type="text/plain")


@csrf_exempt
def update_host_bmc(request, lab_name="", host_id=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    if request.method == "POST":
        # update / create RemoteInfo for host
        return JsonResponse(
            lab_manager.update_host_remote_info(request.POST, host_id),
            safe=False
        )


def lab_profile(request, lab_name=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    return JsonResponse(lab_manager.get_profile(), safe=False)


@csrf_exempt
def specific_task(request, lab_name="", job_id="", task_id=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    LabManagerTracker.get(lab_name, lab_token)  # Authorize caller, but we dont need the result

    if request.method == "POST":
        task = get_task(task_id)
        if 'status' in request.POST:
            task.status = request.POST.get('status')
        if 'message' in request.POST:
            task.message = request.POST.get('message')
        if 'lab_token' in request.POST:
            task.lab_token = request.POST.get('lab_token')
        task.save()
        NotificationHandler.task_updated(task)
        d = {}
        d['task'] = task.config.get_delta()
        m = {}
        m['status'] = task.status
        m['job'] = str(task.job)
        m['message'] = task.message
        d['meta'] = m
        return JsonResponse(d, safe=False)
    elif request.method == "GET":
        return JsonResponse(get_task(task_id).config.get_delta())


@csrf_exempt
def specific_job(request, lab_name="", job_id=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    if request.method == "POST":
        return JsonResponse(lab_manager.update_job(job_id, request.POST), safe=False)
    return JsonResponse(lab_manager.get_job(job_id), safe=False)


def new_jobs(request, lab_name=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    return JsonResponse(lab_manager.get_new_jobs(), safe=False)


def current_jobs(request, lab_name=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    return JsonResponse(lab_manager.get_current_jobs(), safe=False)


def lab_downtime(request, lab_name=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
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


def done_jobs(request, lab_name=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    return JsonResponse(lab_manager.get_done_jobs(), safe=False)
