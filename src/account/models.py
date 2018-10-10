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
    UP = 0
    TEMP_DOWN = 100
    DOWN = 200


def upload_to(object, filename):
    return object.user.username + '/' + filename

class UserProfile(models.Model):
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
    # list of length 4096 containing either 0 (not available) or 1 (available)
    vlans = models.TextField()
    block_size = models.IntegerField()
    allow_overlapping = models.BooleanField()
    # list of length 4096 containing either 0 (not rexerved) or 1 (reserved)
    reserved_vlans = models.TextField()

    def get_vlan(self, count=1):
        allocated = []
        vlans = json.loads(self.vlans)
        for i in range(count):
            new_vlan = vlans.index(1)  # will throw if none available
            vlans[new_vlan] = 0
            allocated.append(new_vlan)
        if count is 1:
            return allocated[0]
        return allocated

    def get_public_vlan(self):
        return PublicNetwork.objects.filter(lab=self.lab_set.first(), in_use=False).first()

    def reserve_public_vlan(self, vlan):
        net = PublicNetwork.objects.get(lab=self.lab_set.first(), vlan=vlan, in_use=False)
        net.in_use = True
        net.save()

    def release_public_vlan(self, vlan):
        net = PublicNetwork.objects.get(lab=self.lab_set.first(), vlan=vlan, in_use=True)
        net.in_use = False
        net.save()

    def public_vlan_is_available(self, vlan):
        net = PublicNetwork.objects.get(lab=self.lab_set.first(), vlan=vlan)
        return not net.in_use


    def is_available(self, vlans):
        """
        'vlans' is either a single vlan id integer or a list of integers
        will return true (available) or false
        """
        if self.allow_overlapping:
            return True

        reserved = json.loads(self.reserved_vlans)
        vlan_master_list = json.loads(self.vlans)
        try:
            iter(vlans)
        except:
            vlans = [vlans]

        for vlan in vlans:
            if not vlan_master_list[vlan] or reserved[vlan]:
                return False
        return True

    def release_vlans(self, vlans):
        """
        'vlans' is either a single vlan id integer or a list of integers
        will make the vlans available
        doesnt return a value
        """
        my_vlans = json.loads(self.vlans)

        try:
            iter(vlans)
        except:
            vlans = [vlans]

        for vlan in vlans:
            my_vlans[vlan] = 1
        self.vlans = json.dumps(my_vlans)
        self.save()

    def reserve_vlans(self, vlans):
        my_vlans = json.loads(self.vlans)

        try:
            iter(vlans)
        except:
            vlans = [vlans]

        vlans = set(vlans)

        for vlan in vlans:
            if my_vlans[vlan] is 0:
                raise ValueError("vlan " + str(vlan) + " is not available")

            my_vlans[vlan] = 0
        self.vlans = json.dumps(my_vlans)
        self.save()



class Lab(models.Model):
    lab_user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, primary_key=True, unique=True, null=False, blank=False)
    contact_email = models.EmailField(max_length=200, null=True, blank=True)
    contact_phone = models.CharField(max_length=20, null=True, blank=True)
    status = models.IntegerField(default=LabStatus.UP)
    vlan_manager = models.ForeignKey(VlanManager, on_delete=models.CASCADE, null=True)
    location = models.TextField(default="unknown")
    api_token = models.CharField(max_length=50)
    description = models.CharField(max_length=240)

    @staticmethod
    def make_api_token():
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        key = ""
        for i in range(45):
            key += random.choice(alphabet)
        return key


    def __str__(self):
        return self.name


class PublicNetwork(models.Model):
    vlan = models.IntegerField()
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    in_use = models.BooleanField(default=False)
    cidr = models.CharField(max_length=50, default="0.0.0.0/0")
    gateway = models.CharField(max_length=50, default="0.0.0.0")
