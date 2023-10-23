##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

# HTTP Requests from the user will need to be processed here first, before the appropriate liblaas endpoint is called

from account.models import UserProfile
from liblaas.views import *
from liblaas.utils import validate_collaborators
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
from booking.models import Booking
from account.models import Lab
from django.utils import timezone
from datetime import timedelta
from laas_dashboard.settings import PROJECT

def request_list_flavors(request) -> HttpResponse:
    data = json.loads(request.body.decode('utf-8'))
    if not "project" in data:
        return HttpResponse(status=422)

    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    response = flavor_list_flavors(data["project"])
    return JsonResponse(status=200, data={"flavors_list": response})


def request_list_template(request) -> HttpResponse:
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    
    uid = UserProfile.objects.get(user=request.user)
    uid = uid.ipa_username

    response = template_list_templates(uid)
    return JsonResponse(status=200, data={"templates_list": response})

def request_create_template(request) -> HttpResponse:
    data = json.loads(request.body.decode('utf-8'))
    if not "template_blob" in data:
        return HttpResponse(status=422)

    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    response = template_make_template(data["template_blob"])
    return JsonResponse(status=200, data={"uuid": response})

def request_create_booking(request) -> HttpResponse:
    # Validate request
    data = json.loads(request.body.decode('utf-8'))
    if not "booking_blob" in data:
        return HttpResponse(status=422)

    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    
    data = data["booking_blob"]

    # Validate and build collaborators list
    valid = validate_collaborators(data["allowed_users"])
    if (not valid["valid"]):
        return JsonResponse(
            data={"message": valid["message"], "error": True},
            status=200,
            safe=False
        )
    ipa_users = []
    ipa_users.append(UserProfile.objects.get(user=request.user).ipa_username)
    for user in data["allowed_users"]:
        collab_profile = UserProfile.objects.get(user=User.objects.get(username=user))
        ipa_users.append(collab_profile.ipa_username)

    # Reformat post data
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
    },
    "origin": PROJECT
    }

    # Create booking in dashboard
    booking = Booking.objects.create(
    purpose=bookingBlob["metadata"]["purpose"],
    project=bookingBlob["metadata"]['project'],
    lab=Lab.objects.get(name='UNH_IOL'),
    owner=request.user,
    start=timezone.now(),
    end=timezone.now() + timedelta(days=int(bookingBlob["metadata"]['length'])),
    )

    for c in list(data["allowed_users"]):
        booking.collaborators.add(User.objects.get(username=c))
    
    # Create booking in liblaas
    bookingBlob["metadata"]["booking_id"] = str(booking.id)
    liblaas_response = booking_create_booking(bookingBlob)
    if liblaas_response.status_code != 200:
        print("received non success from liblaas, deleting booking from dashboard")
        booking.delete()
        return JsonResponse(
            data={},
            status=500,
            safe=False
        )
    
    aggregateId = liblaas_response
    booking.aggregateId = aggregateId
    booking.save()

    print(f"Created new booking with id {booking.id} and aggregate {aggregateId}")

    return JsonResponse(
        data = {"bookingId": booking.id},
        status=200,
        safe=False
    )

def request_migrate_new(request) -> HttpResponse:
    user = request.user
    profile = UserProfile.objects.get(user=user)

    data = json.loads(request.body.decode('utf-8'))
    fn = data["firstname"].strip()
    ln = data["lastname"].strip()
    company = data["company"].strip()

    if (fn == "" or ln == "" or company == ""):
        return JsonResponse(
        data = {"message": "Please fill out all fields."},
        status=406
        )
    
    user_blob = {
        "uid": str(user), # For this case, the username is not taken, so the dashboard username will be used
        "givenname": str(fn),
        "sn": str(ln),
        "ou": str(company),
        "mail": str(profile.email_addr),
        'random': True
    }
    
    vpn_username = user_create_user(user_blob)

    if (vpn_username):
        profile.ipa_username = vpn_username
        profile.save()
        return HttpResponse(status=200)

    return JsonResponse(
        data = {"message": "Unable to create account. Please try again."},
        status=406
    )



def request_migrate_conflict(request) -> HttpResponse:
    user = request.user
    profile = UserProfile.objects.get(user=user)

    data = json.loads(request.body.decode('utf-8'))
    fn = data["firstname"].strip()
    ln = data["lastname"].strip()
    company = data["company"].strip()
    username = data["username"].strip()

    if (fn == "" or ln == "" or company == "" or username == ""):
        return JsonResponse(
        data = {"message": "Please fill out all fields."},
        status=406
        )
    
    # Check if username is taken by querying for that user
    existing_user = user_get_user(username)
    if (existing_user):
        return JsonResponse(
        data = {"message": "Username is already taken. Please try again."},
        status=406
        )
    
    # Create and link account
    user_blob = {
        "uid": str(username),
        "givenname": str(fn),
        "sn": str(ln),
        "ou": str(company),
        "mail": str(profile.email_addr),
        'random': True
    }
    
    vpn_username = user_create_user(user_blob)

    if (vpn_username):
        profile.ipa_username = vpn_username
        profile.save()
        return HttpResponse(status=200)

    return JsonResponse(
        data = {"message": "Unable to create account. Please try again."},
        status=406
    )

def request_set_company(request):
    data = json.loads(request.body.decode('utf-8'))
    if not "data" in data:
        return HttpResponse(status=422)

    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    
    up = UserProfile.objects.get(user=request.user)
    success = user_set_company(up.ipa_username, data["data"].strip())

    if (success):
        return HttpResponse(status=200)
    
    return JsonResponse(
        data = {"message": "Unable to update details. Please check your input and try again."},
        status=406
    )

def request_set_ssh(request):
    data = json.loads(request.body.decode('utf-8')) 
    if not "data" in data:
        return HttpResponse(status=422)

    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    up = UserProfile.objects.get(user=request.user)
    success = user_set_ssh(up.ipa_username, data["data"])
    
    if (success):
        return HttpResponse(status=200)
    
    # API does not provide a way to verify keys were successfully added, so it is unlikely that this case will ever be hit
    return JsonResponse(
        data = {"message": "Unable to add SSH key. Please verify that the key is valid and try again."},
        status=406
    )

