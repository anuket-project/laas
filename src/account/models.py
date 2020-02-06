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
import json
import random


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
    ssh_public_key = models.FileField(upload_to=upload_to, null=True, blank=True)
    pgp_public_key = models.FileField(upload_to=upload_to, null=True, blank=True)
    email_addr = models.CharField(max_length=300, blank=False, default='email@mail.com')
    company = models.CharField(max_length=200, blank=False)

    oauth_token = models.CharField(max_length=1024, blank=False)
    oauth_secret = models.CharField(max_length=1024, blank=False)

    jira_url = models.CharField(max_length=100, default='')
    full_name = models.CharField(max_length=100, default='')
    booking_privledge = models.BooleanField(default=False)

    class Meta:
        db_table = 'user_profile'

    def __str__(self):
        return self.user.username


class VlanManager(models.Model):
    """
    Keeps track of the vlans for a lab.

    Vlans are represented as indexes into a 4096 element list.
    This list is serialized to JSON for storing in the DB.
    """

    # list of length 4096 containing either 0 (not available) or 1 (available)
    vlans = models.TextField()
    # list of length 4096 containing either 0 (not reserved) or 1 (reserved)
    reserved_vlans = models.TextField()

    block_size = models.IntegerField()

    # True if the lab allows two different users to have the same private vlans
    # if they use QinQ or a vxlan overlay, for example
    allow_overlapping = models.BooleanField()

    def get_vlan(self, count=1):
        """
        Return the ID of available vlans, but does not reserve them.

        Will throw index exception if not enough vlans are available.
        If count == 1, the return value is an int. Otherwise, it is a list of ints.
        """
        allocated = []
        vlans = json.loads(self.vlans)
        for i in range(count):
            new_vlan = vlans.index(1)  # will throw if none available
            vlans[new_vlan] = 0
            allocated.append(new_vlan)
        if count == 1:
            return allocated[0]
        return allocated

    def get_public_vlan(self):
        """Return reference to an available public network without reserving it."""
        return PublicNetwork.objects.filter(lab=self.lab_set.first(), in_use=False).first()

    def reserve_public_vlan(self, vlan):
        """Reserves the Public Network that has the given vlan."""
        net = PublicNetwork.objects.get(lab=self.lab_set.first(), vlan=vlan, in_use=False)
        net.in_use = True
        net.save()

    def release_public_vlan(self, vlan):
        """Un-reserves a public network with the given vlan."""
        net = PublicNetwork.objects.get(lab=self.lab_set.first(), vlan=vlan, in_use=True)
        net.in_use = False
        net.save()

    def public_vlan_is_available(self, vlan):
        """
        Whether the public vlan is available.

        returns true if the network with the given vlan is free to use,
        False otherwise
        """
        net = PublicNetwork.objects.get(lab=self.lab_set.first(), vlan=vlan)
        return not net.in_use

    def is_available(self, vlans):
        """
        If the vlans are available.

        'vlans' is either a single vlan id integer or a list of integers
        will return true (available) or false
        """
        if self.allow_overlapping:
            return True

        reserved = json.loads(self.reserved_vlans)
        vlan_master_list = json.loads(self.vlans)
        try:
            iter(vlans)
        except Exception:
            vlans = [vlans]

        for vlan in vlans:
            if not vlan_master_list[vlan] or reserved[vlan]:
                return False
        return True

    def release_vlans(self, vlans):
        """
        Make the vlans available for another booking.

        'vlans' is either a single vlan id integer or a list of integers
        will make the vlans available
        doesnt return a value
        """
        my_vlans = json.loads(self.vlans)

        try:
            iter(vlans)
        except Exception:
            vlans = [vlans]

        for vlan in vlans:
            my_vlans[vlan] = 1
        self.vlans = json.dumps(my_vlans)
        self.save()

    def reserve_vlans(self, vlans):
        """
        Reserves all given vlans or throws a ValueError.

        vlans can be an integer or a list of integers.
        """
        my_vlans = json.loads(self.vlans)

        try:
            iter(vlans)
        except Exception:
            vlans = [vlans]

        vlans = set(vlans)

        for vlan in vlans:
            if my_vlans[vlan] == 0:
                raise ValueError("vlan " + str(vlan) + " is not available")

            my_vlans[vlan] = 0
        self.vlans = json.dumps(my_vlans)
        self.save()


class Lab(models.Model):
    """
    Model representing a Hosting Lab.

    Anybody that wants to host resources for LaaS needs to have a Lab model
    We associate hardware with Labs so we know what is available and where.
    """

    lab_user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, primary_key=True, unique=True, null=False, blank=False)
    contact_email = models.EmailField(max_length=200, null=True, blank=True)
    contact_phone = models.CharField(max_length=20, null=True, blank=True)
    status = models.IntegerField(default=LabStatus.UP)
    vlan_manager = models.ForeignKey(VlanManager, on_delete=models.CASCADE, null=True)
    location = models.TextField(default="unknown")
    # This token must apear in API requests from this lab
    api_token = models.CharField(max_length=50)
    description = models.CharField(max_length=240)

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


class PublicNetwork(models.Model):
    """L2/L3 network that can reach the internet."""

    vlan = models.IntegerField()
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    in_use = models.BooleanField(default=False)
    cidr = models.CharField(max_length=50, default="0.0.0.0/0")
    gateway = models.CharField(max_length=50, default="0.0.0.0")


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
