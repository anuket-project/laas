##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from django.contrib.postgres.fields import JSONField
from django.http import HttpResponseNotFound
from django.urls import reverse
from django.utils import timezone

import json
import uuid
import yaml
import re

from booking.models import Booking
from account.models import Downtime, UserProfile
from dashboard.utils import AbstractModelQuery



class LabManagerTracker:

    @classmethod
    def get(cls, lab_name, token):
        """
        Get a LabManager.

        Takes in a lab name (from a url path)
        returns a lab manager instance for that lab, if it exists
        Also checks that the given API token is correct
        """
        try:
            lab = Lab.objects.get(name=lab_name)
        except Exception:
            raise PermissionDenied("Lab not found")
        if lab.api_token == token:
            return LabManager(lab)
        raise PermissionDenied("Lab not authorized")


class LabManager:
    """
    Handles all lab REST calls.

    handles jobs, inventory, status, etc
    may need to create helper classes
    """

    def __init__(self, lab):
        self.lab = lab

    def get_downtime(self):
        return Downtime.objects.filter(start__lt=timezone.now(), end__gt=timezone.now(), lab=self.lab)

    def get_downtime_json(self):
        downtime = self.get_downtime().first()  # should only be one item in queryset
        if downtime:
            return {
                "is_down": True,
                "start": downtime.start,
                "end": downtime.end,
                "description": downtime.description
            }
        return {"is_down": False}

    def create_downtime(self, form):
        """
        Create a downtime event.

        Takes in a dictionary that describes the model.
        {
          "start": utc timestamp
          "end": utc timestamp
          "description": human text (optional)
        }
        For timestamp structure, https://docs.djangoproject.com/en/2.2/ref/forms/fields/#datetimefield
        """
        Downtime.objects.create(
            start=form.cleaned_data['start'],
            end=form.cleaned_data['end'],
            description=form.cleaned_data['description'],
            lab=self.lab
        )
        return self.get_downtime_json()

    def get_profile(self):
        prof = {}
        prof['name'] = self.lab.name
        prof['contact'] = {
            "phone": self.lab.contact_phone,
            "email": self.lab.contact_email
        }
        prof['host_count'] = [{
            "type": profile.name,
            "count": len(profile.get_resources(lab=self.lab))}
            for profile in ResourceProfile.objects.filter(labs=self.lab)]
        return prof

    def format_user(self, userprofile):
        return {
            "id": userprofile.user.id,
            "username": userprofile.user.username,
            "email": userprofile.email_addr,
            "first_name": userprofile.user.first_name,
            "last_name": userprofile.user.last_name,
            "company": userprofile.company
        }

    def get_users(self):
        userlist = [self.format_user(profile) for profile in UserProfile.objects.select_related("user").all()]

        return json.dumps({"users": userlist})

    def get_user(self, user_id):
        user = User.objects.get(pk=user_id)

        profile = get_object_or_404(UserProfile, user=user)

        return json.dumps(self.format_user(profile))

    def get_status(self):
        return {"status": self.lab.status}

    def set_status(self, payload):
        {}

class APILog(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    call_time = models.DateTimeField(auto_now=True)
    method = models.CharField(null=True, max_length=6)
    endpoint = models.CharField(null=True, max_length=300)
    ip_addr = models.GenericIPAddressField(protocol="both", null=True, unpack_ipv4=False)
    body = JSONField(null=True)

    def __str__(self):
        return "Call to {} at {} by {}".format(
            self.endpoint,
            self.call_time,
            self.user.username
        )


class AutomationAPIManager:
    @staticmethod
    def serialize_booking(booking):
        sbook = {}
        sbook['id'] = booking.pk
        sbook['owner'] = booking.owner.username
        sbook['collaborators'] = [user.username for user in booking.collaborators.all()]
        sbook['start'] = booking.start
        sbook['end'] = booking.end
        sbook['lab'] = AutomationAPIManager.serialize_lab(booking.lab)
        sbook['purpose'] = booking.purpose
        return sbook

    @staticmethod
    def serialize_lab(lab):
        slab = {}
        slab['id'] = lab.pk
        slab['name'] = lab.name
        return slab

    @staticmethod
    def serialize_userprofile(up):
        sup = {}
        sup['id'] = up.pk
        sup['username'] = up.user.username
        return sup

# Needs to exist for migrations
def get_task_uuid():
    pass