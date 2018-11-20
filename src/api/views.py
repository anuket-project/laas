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
from django.views import View
from django.http.response import JsonResponse
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from django.views.decorators.csrf import csrf_exempt

from api.serializers.booking_serializer import BookingSerializer
from api.serializers.old_serializers import UserSerializer
from account.models import UserProfile
from booking.models import Booking
from api.models import LabManagerTracker, get_task
from notifier.manager import NotificationHandler


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


def lab_status(request, lab_name=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    if request.method == "POST":
        return JsonResponse(lab_manager.set_status(request.POST), safe=False)
    return JsonResponse(lab_manager.get_status(), safe=False)


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


def done_jobs(request, lab_name=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    return JsonResponse(lab_manager.get_done_jobs(), safe=False)
