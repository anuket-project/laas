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
import math
import os
import traceback
import sys
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views import View
from django.http import HttpResponseNotFound
from django.http.response import JsonResponse, HttpResponse
import requests
from api.utils import ipa_query_user, ipa_set_ssh, ipa_set_company
from rest_framework.authtoken.models import Token
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.contrib.auth.models import User

from api.forms import DowntimeForm
from account.models import UserProfile, Lab
from booking.models import Booking
from api.models import LabManagerTracker,AutomationAPIManager, APILog

import yaml
import uuid
from deepmerge import Merger

"""
API views.

All functions return a Json blob
Most functions that deal with info from a specific lab (tasks, host info)
requires the Lab auth token.
    for example, curl -H auth-token:mylabsauthtoken url

Most functions let you GET or POST to the same endpoint, and
the correct thing will happen
"""

liblaas_base_url = os.environ.get('LIBLAAS_BASE_URL')
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


def lab_profile(request, lab_name=""):
    lab_token = request.META.get('HTTP_AUTH_TOKEN')
    lab_manager = LabManagerTracker.get(lab_name, lab_token)
    return JsonResponse(lab_manager.get_profile(), safe=False)



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


def auth_and_log(request, endpoint):
    """
    Function to authenticate an API user and log info
    in the API log model. This is to keep record of
    all calls to the dashboard
    """
    user_token = request.META.get('HTTP_AUTH_TOKEN')
    response = None

    if user_token is None:
        return HttpResponse('Unauthorized', status=401)

    try:
        token = Token.objects.get(key=user_token)
    except Token.DoesNotExist:
        token = None
        # Added logic to detect malformed token
        if len(str(user_token)) != 40:
            response = HttpResponse('Malformed Token', status=401)
        else:
            response = HttpResponse('Unauthorized', status=401)

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
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
Booking API Views
"""


def user_bookings(request):
    # token = auth_and_log(request, 'booking')

    # if isinstance(token, HttpResponse):
    #     return token

    # bookings = Booking.objects.filter(owner=token.user, end__gte=timezone.now())
    # output = [AutomationAPIManager.serialize_booking(booking)
    #           for booking in bookings]
    # return JsonResponse(output, safe=False)
    # todo - LL Integration
    return HttpResponse(status=404)


@csrf_exempt
def specific_booking(request, booking_id=""):
    # token = auth_and_log(request, 'booking/{}'.format(booking_id))

    # if isinstance(token, HttpResponse):
    #     return token

    # booking = get_object_or_404(Booking, pk=booking_id, owner=token.user)
    # if request.method == "GET":
    #     sbooking = AutomationAPIManager.serialize_booking(booking)
    #     return JsonResponse(sbooking, safe=False)

    # if request.method == "DELETE":

    #     if booking.end < timezone.now():
    #         return HttpResponse("Booking already over", status=400)

    #     booking.end = timezone.now()
    #     booking.save()
    #     return HttpResponse("Booking successfully cancelled")
    # todo - LL Integration
    return HttpResponse(status=404)


@csrf_exempt
def extend_booking(request, booking_id="", days=""):
    token = auth_and_log(request, 'booking/{}/extendBooking/{}'.format(booking_id, days))

    if isinstance(token, HttpResponse):
        return token

    booking = get_object_or_404(Booking, pk=booking_id, owner=token.user)

    if booking.end < timezone.now():
        return HttpResponse("This booking is already over, cannot extend")

    if days > 30:
        return HttpResponse("Cannot extend a booking longer than 30 days")

    if booking.ext_count == 0:
        return HttpResponse("Booking has already been extended 2 times, cannot extend again")

    booking.end += timedelta(days=days)
    booking.ext_count -= 1
    booking.save()

    return HttpResponse("Booking successfully extended")


@csrf_exempt
def make_booking(request):
    print("received call to make_booking")
    data = json.loads(request.body)
    print("incoming data is ", data)

    # todo - test this
    ipa_users = list(UserProfile.objects.get(user=request.user).ipa_username) # add owner's ipa username to list of allowed users to be sent to liblaas

    for user in list(data["allowed_users"]):
        collab_profile = UserProfile.objects.get(user=User.objects.get(username=user))
        if (collab_profile.ipa_username == "" or collab_profile.ipa_username == None):
            return JsonResponse(
            data={},
            status=406, # Not good practice but a quick solution until blob validation is fully supported within django instead of the frontend
            safe=False
        )
        else:
            ipa_users.append(collab_profile.ipa_username)

    bookingBlob = {
        "template_id": data["template_id"],
        "allowed_users": ipa_users,
        "global_cifile": data["global_cifile"],
        "metadata": {
            "booking_id": None, # fill in after creating django object
            "owner": UserProfile.objects.get(user=request.user).ipa_username,
            "lab": "UNH_IOL",
            "purpose": data["metadata"]["purpose"],
            "project": data["metadata"]["project"],
            "length": int(data["metadata"]["length"])
        }
    }
    
    print("allowed users are ", bookingBlob["allowed_users"])
    try:
        booking = Booking.objects.create(
        purpose=bookingBlob["metadata"]["purpose"],
        project=bookingBlob["metadata"]['project'],
        lab=Lab.objects.get(name='UNH_IOL'),
        owner=request.user,
        start=timezone.now(),
        end=timezone.now() + timedelta(days=int(bookingBlob["metadata"]['length'])),
        )
        print("successfully created booking object with id ", booking.id)

        # Now add collabs
        for c in list(data["allowed_users"]):
            booking.collaborators.add(User.objects.get(username=c))
        print("successfully added collabs")

        # Now create it in liblaas
        bookingBlob["metadata"]["booking_id"] = str(booking.id)
        liblaas_endpoint = os.environ.get("LIBLAAS_BASE_URL") + 'booking/create'
        liblaas_response = requests.post(liblaas_endpoint, data=json.dumps(bookingBlob), headers={'Content-Type': 'application/json'})
        if liblaas_response.status_code != 200:
            print("received non success from liblaas")
            return JsonResponse(
            data={},
            status=500,
            safe=False
        ) 
        aggregateId = json.loads(liblaas_response.content)
        print("successfully created aggregate in liblaas")

        # Now update the agg_id
        booking.aggregateId = aggregateId
        booking.save()
        print("sucessfully updated aggreagateId in booking object")

        return JsonResponse(
            data = {"bookingId": booking.id},
            status=200,
            safe=False
        )
    except Exception as error:
        print(error)
        return JsonResponse(
            data={},
            status=500,
            safe=False
        ) 


"""
Resource Inventory API Views
"""
# todo - LL Integration

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


"""
Booking Details API Views
"""


def booking_details(request, booking_id=""):
    # token = auth_and_log(request, 'booking/{}/details'.format(booking_id))

    # if isinstance(token, HttpResponse):
    #     return token

    # booking = get_object_or_404(Booking, pk=booking_id, owner=token.user)

    # # overview
    # overview = {
    #     'username': GeneratedCloudConfig._normalize_username(None, str(token.user)),
    #     'purpose': booking.purpose,
    #     'project': booking.project,
    #     'start_time': booking.start,
    #     'end_time': booking.end,
    #     'pod_definitions': booking.resource.template,
    #     'lab': booking.lab
    # }

    # # deployment progress
    # task_list = []
    # for task in booking.job.get_tasklist():
    #     task_info = {
    #         'name': str(task),
    #         'status': 'DONE',
    #         'lab_response': 'No response provided (yet)'
    #     }
    #     if task.status < 100:
    #         task_info['status'] = 'PENDING'
    #     elif task.status < 200:
    #         task_info['status'] = 'IN PROGRESS'

    #     if task.message:
    #         if task.type_str == "Access Task" and request.user.id != task.config.user.id:
    #             task_info['lab_response'] = '--secret--'
    #         else:
    #             task_info['lab_response'] = str(task.message)
    #     task_list.append(task_info)

    # # pods
    # pod_list = []
    # for host in booking.resource.get_resources():
    #     pod_info = {
    #         'hostname': host.config.name,
    #         'machine': host.name,
    #         'role': '',
    #         'is_headnode': host.config.is_head_node,
    #         'image': host.config.image,
    #         'ram': {'amount': str(host.profile.ramprofile.first().amount) + 'G', 'channels': host.profile.ramprofile.first().channels},
    #         'cpu': {'arch': host.profile.cpuprofile.first().architecture, 'cores': host.profile.cpuprofile.first().cores, 'sockets': host.profile.cpuprofile.first().cpus},
    #         'disk': {'size': str(host.profile.storageprofile.first().size) + 'GiB', 'type': host.profile.storageprofile.first().media_type, 'mount_point': host.profile.storageprofile.first().name},
    #         'interfaces': [],
    #     }
    #     try:
    #         pod_info['role'] = host.template.opnfvRole
    #     except Exception:
    #         pass
    #     for intprof in host.profile.interfaceprofile.all():
    #         int_info = {
    #             'name': intprof.name,
    #             'speed': intprof.speed
    #         }
    #         pod_info['interfaces'].append(int_info)
    #     pod_list.append(pod_info)

    # # diagnostic info
    # diagnostic_info = {
    #     'job_id': booking.job.id,
    #     'ci_files': '',
    #     'pods': []
    # }
    # for host in booking.resource.get_resources():
    #     pod = {
    #         'host': host.name,
    #         'configs': [],

    #     }
    #     for ci_file in host.config.cloud_init_files.all():
    #         ci_info = {
    #             'id': ci_file.id,
    #             'text': ci_file.text
    #         }
    #         pod['configs'].append(ci_info)
    #     diagnostic_info['pods'].append(pod)

    # details = {
    #     'overview': overview,
    #     'deployment_progress': task_list,
    #     'pods': pod_list,
    #     'diagnostic_info': diagnostic_info,
    #     'pdf': booking.pdf
    # }
    # return JsonResponse(str(details), safe=False)
    # todo - LL Integration
    return HttpResponse(status=404)


""" Forwards a request to the LibLaaS API from a workflow """
def liblaas_request(request) -> JsonResponse:
    print("handing liblaas request... ", request.method)
    print(request.body)
    if request.method != 'POST':
        return JsonResponse({"error" : "405 Method not allowed"})

    liblaas_base_url = os.environ.get("LIBLAAS_BASE_URL")
    post_data = json.loads(request.body)
    print("post data is " + str(post_data))
    http_method = post_data["method"]
    liblaas_endpoint = post_data["endpoint"]
    payload = post_data["workflow_data"]
    # Fill in actual username
    liblaas_endpoint = liblaas_endpoint.replace("[username]", UserProfile.objects.get(user=request.user).ipa_username)
    liblaas_endpoint = liblaas_base_url + liblaas_endpoint
    print("processed endpoint is ", liblaas_endpoint)

    if (http_method == "GET"):
        response = requests.get(liblaas_endpoint, data=json.dumps(payload))
    elif (http_method == "POST"):
        response = requests.post(liblaas_endpoint, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
    elif (http_method == "DELETE"):
        response = requests.delete(liblaas_endpoint, data=json.dumps(payload))
    elif (http_method == "PUT"):
        response = requests.put(liblaas_endpoint, data=json.dumps(payload))
    else:
        return JsonResponse(
            data={},
            status=405,
            safe=False
        )
    try:
        return JsonResponse(
            data=json.loads(response.content.decode('utf8')),
            status=200,
            safe=False
        )
    except Exception as e:
        print("fail")
        print(e)
        return JsonResponse(
            data = {},
            status=500,
            safe=False
        )

def liblaas_templates(request):
    liblaas_url = os.environ.get("LIBLAAS_BASE_URL") + "template/list/" + UserProfile.objects.get(user=request.user).ipa_username
    print("api call to " + liblaas_url)
    return requests.get(liblaas_url)

def delete_template(request):
    endpoint = json.loads(request.body)["endpoint"]
    liblaas_url = os.environ.get("LIBLAAS_BASE_URL") + endpoint
    print("api call to ", liblaas_url)
    try:
        response = requests.delete(liblaas_url)
        return JsonResponse(
            data={},
            status=response.status_code,
            safe=False
        )
    except:
        return JsonResponse(
            data={},
            status=500,
            safe=False
        )

def get_booking_status(bookingObject):
    liblaas_url =  os.environ.get("LIBLAAS_BASE_URL") + "booking/" + bookingObject.aggregateId + "/status"
    print("Getting booking status at: ", liblaas_url)
    response = requests.get(liblaas_url)
    try:
        return json.loads(response.content)
    except:
        print("failed to get status")
        return []
    
def liblaas_end_booking(aggregateId):
    liblaas_url = os.environ.get('LIBLAAS_BASE_URL') + "booking/" + str(aggregateId) + "/end"
    print("Ending booking at ", liblaas_url)
    response = requests.delete(liblaas_url)
    try:
        return response
    except:
        print("failed to end booking")
        return HttpResponse(status=500)
    
def ipa_create_account(request):
    # Called when no username was found
    # Only allow if user does not have a linked ipa account
    profile =  UserProfile.objects.get(user=request.user)
    if (profile.ipa_username):
        return HttpResponse(status=401)

    post_data = request.POST
    user = {
        'uid': str(request.user),
        'givenname': post_data['first_name'],
        'sn': post_data['last_name'],
        'cn': post_data['first_name'] + " " + post_data['last_name'],
        'mail': post_data['email'],
        'ou': post_data['company'],
        'random': True
    }

    try:
        response = requests.post(liblaas_base_url + "user/create", data=json.dumps(user), headers={'Content-Type': 'application/json'})
        profile.ipa_username = user['uid']
        print("Saving ipa username", profile.ipa_username)
        profile.save()
        return redirect("dashboard:index")
    except Exception as e:
        print(e)
        return redirect("dashboard:index")
    
def ipa_confirm_account(request):
    # Called when username was found and email matches
    profile =  UserProfile.objects.get(user=request.user)
    if (profile.ipa_username):
        return HttpResponse(status=401)
    
    profile.ipa_username = str(request.user)
    print("Saving ipa username", profile.ipa_username)
    profile.save()
    return redirect("dashboard:index")

def ipa_conflict_account(request):
    # Called when username was found but emails do not match
    # Need to ask user to input alternate username
    # To verify username is not taken, call query_username and accept if returns None
    print("ipa conflict account")
    profile =  UserProfile.objects.get(user=request.user)
    print("profile is", profile)
    if (profile.ipa_username):
        return HttpResponse(status=401)

    post_data = request.POST
    user = {
        'uid': post_data['ipa_username'],
        'givenname': post_data['first_name'],
        'sn': post_data['last_name'],
        'cn': post_data['first_name'] + " " + post_data['last_name'],
        'mail': post_data['email'],
        'ou': post_data['company'],
        'random': True,
    }

    try:
        response = requests.post(liblaas_base_url + "user/create", data=json.dumps(user), headers={'Content-Type': 'application/json'})
        profile.ipa_username = user['uid']
        print("Saving ipa username", profile.ipa_username)
        profile.save()
        return redirect("dashboard:index")
    except Exception as e:
        print(e)
        return redirect("dashboard:index")

def ipa_set_company_from_workflow(request):
    profile = UserProfile.objects.get(user=request.user)
    ipa_set_company(profile, request.POST["company"])
    return redirect("workflow:book_a_pod")

def ipa_add_ssh_from_workflow(request):
    profile = UserProfile.objects.get(user=request.user)
    key_as_list = []
    key_as_list.append(request.POST["ssh_public_key"])
    ipa_set_ssh(profile, key_as_list)
    return redirect("workflow:book_a_pod")
