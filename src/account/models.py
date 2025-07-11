##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.contrib.auth.models import User
from django.db import models
from django.apps import apps
import json
import random
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from collections import Counter

class LabStatus(object):
    """
    A Poor man's enum for the status of a lab.

    If everything is working fine at a lab, it is UP.
    If it is down temporarily e.g. for maintenance, it is TEMP_DOWN
    If its broken, its DOWN
    """

    UP = 0
    TEMP_DOWN = 100
    DOWN = 200


def upload_to(object, filename):
    return object.user.username + '/' + filename


class UserProfile(models.Model):
    """Extend the Django User model."""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    timezone = models.CharField(max_length=100, blank=False, default='UTC')
    email_addr = models.CharField(max_length=300, blank=False, default='email@mail.com')

    oauth_token = models.CharField(max_length=1024, blank=False)
    oauth_secret = models.CharField(max_length=1024, blank=False)

    full_name = models.CharField(max_length=100, null=True, blank=True, default='')
    booking_privledge = models.BooleanField(default=False)

    public_user = models.BooleanField(default=False)
    ipa_username = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'user_profile'

    def __str__(self):
        return self.user.username
    @staticmethod
    def create_tokens_for_all():
        for user in User.objects.all():
            Token.objects.get_or_create(user=user)
    @receiver(post_save, sender=settings.AUTH_USER_MODEL)
    def auth_token_signal(sender, instance=None, created=False, **kwargs):
        if created:
            Token.objects.create(user=instance)

class Lab(models.Model):
    """
    Model representing a Hosting Lab.

    Anybody that wants to host resources for LaaS needs to have a Lab model
    We associate hardware with Labs so we know what is available and where.
    """

    lab_user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, primary_key=True, unique=True, null=False, blank=False)
    contact_email = models.EmailField(max_length=200, null=True, blank=True)
    status = models.IntegerField(default=LabStatus.UP)
    location = models.TextField(default="unknown")
    # This token must apear in API requests from this lab
    api_token = models.CharField(max_length=50)
    description = models.CharField(max_length=240)
    # An info_link is to the lab's page about their services, while the home_link is too their page
        # For the IoL the info_link would be to the confluence wiki page, while the home_link would go to www.iol.uhh.edu
    lab_info_link = models.URLField(null=True)
    lab_home_link = models.URLField(null=True)
    lab_logo_link = models.URLField(null=True, help_text="Remote image resource, size will be constricted dynamically")
    project = models.CharField(default='LaaS', max_length=100)
    about_text = models.TextField(default="")

    @staticmethod
    def make_api_token():
        """Generate random 45 character string for API token."""
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        key = ""
        for i in range(45):
            key += random.choice(alphabet)
        return key

    def __str__(self):
        return self.name

class Downtime(models.Model):
    """
    A Downtime event.

    Labs can create Downtime objects so the dashboard can
    alert users that the lab is down, etc
    """

    start = models.DateTimeField()
    end = models.DateTimeField()
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    description = models.TextField(default="This lab will be down for maintenance")

    def save(self, *args, **kwargs):
        if self.start >= self.end:
            raise ValueError('Start date is after end date')

        # check for overlapping downtimes
        overlap_start = Downtime.objects.filter(lab=self.lab, start__gt=self.start, start__lt=self.end).exists()
        overlap_end = Downtime.objects.filter(lab=self.lab, end__lt=self.end, end__gt=self.start).exists()

        if overlap_start or overlap_end:
            raise ValueError('Overlapping Downtime')

        return super(Downtime, self).save(*args, **kwargs)
