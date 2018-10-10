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
from django.core.validators import RegexValidator

import re

from account.models import Lab


# profile of resources hosted by labs
class HostProfile(models.Model):
    id = models.AutoField(primary_key=True)
    host_type = models.PositiveSmallIntegerField(default=0)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    labs = models.ManyToManyField(Lab, related_name="hostprofiles")

    def validate(self):
        validname = re.compile("^[A-Za-z0-9\-\_\.\/\, ]+$")
        if not validname.match(self.name):
            return "Invalid host profile name given. Name must only use A-Z, a-z, 0-9, hyphens, underscores, dots, commas, or spaces."
        else:
            return None

    def __str__(self):
        return self.name


class InterfaceProfile(models.Model):
    id = models.AutoField(primary_key=True)
    speed = models.IntegerField()
    name = models.CharField(max_length=100)
    host = models.ForeignKey(HostProfile, on_delete=models.DO_NOTHING, related_name='interfaceprofile')
    nic_type = models.CharField(max_length=50, choices=[
        ("onboard", "onboard"),
        ("pcie", "pcie")
        ], default="onboard")

    def __str__(self):
        return self.name + " for " + str(self.host)


class DiskProfile(models.Model):
    id = models.AutoField(primary_key=True)
    size = models.IntegerField()
    media_type = models.CharField(max_length=50, choices=[
        ("SSD", "SSD"),
        ("HDD", "HDD")
    ])
    name = models.CharField(max_length=50)
    host = models.ForeignKey(HostProfile, on_delete=models.DO_NOTHING, related_name='storageprofile')
    rotation = models.IntegerField(default=0)
    interface = models.CharField(max_length=50, choices=[
            ("sata", "sata"),
            ("sas", "sas"),
            ("ssd", "ssd"),
            ("nvme", "nvme"),
            ("scsi", "scsi"),
            ("iscsi", "iscsi"),
        ], default="sata")

    def __str__(self):
        return self.name + " for " + str(self.host)


class CpuProfile(models.Model):
    id = models.AutoField(primary_key=True)
    cores = models.IntegerField()
    architecture = models.CharField(max_length=50, choices=[
        ("x86_64", "x86_64"),
        ("aarch64", "aarch64")
    ])
    cpus = models.IntegerField()
    host = models.ForeignKey(HostProfile, on_delete=models.DO_NOTHING, related_name='cpuprofile')
    cflags = models.TextField(null=True)

    def __str__(self):
        return str(self.architecture) + " " + str(self.cpus) + "S" + str(self.cores) + " C for " + str(self.host)


class RamProfile(models.Model):
    id = models.AutoField(primary_key=True)
    amount = models.IntegerField()
    channels = models.IntegerField()
    host = models.ForeignKey(HostProfile, on_delete=models.DO_NOTHING, related_name='ramprofile')

    def __str__(self):
        return str(self.amount) + "G for " + str(self.host)


##Networking -- located here due to import order requirements
class Network(models.Model):
    id = models.AutoField(primary_key=True)
    vlan_id = models.IntegerField()
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Vlan(models.Model):
    id = models.AutoField(primary_key=True)
    vlan_id = models.IntegerField()
    tagged = models.BooleanField()
    public = models.BooleanField(default=False)

    def __str__(self):
        return str(self.vlan_id) + ("_T" if self.tagged else "")


# Generic resource templates
class GenericResourceBundle(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=300, unique=True)
    xml = models.TextField()
    owner = models.ForeignKey(User, null=True, on_delete=models.DO_NOTHING)
    lab = models.ForeignKey(Lab, null=True, on_delete=models.DO_NOTHING)
    description = models.CharField(max_length=1000, default="")

    def getHosts(self):
        return_hosts = []
        for genericResource in self.generic_resources.all():
            return_hosts.append(genericResource.getHost())

        return return_hosts

    def __str__(self):
        return self.name


class GenericResource(models.Model):
    bundle = models.ForeignKey(GenericResourceBundle, related_name='generic_resources', on_delete=models.DO_NOTHING)
    hostname_validchars = RegexValidator(regex='(?=^.{1,253}$)(?=(^([A-Za-z0-9\-\_]{1,62}\.)*[A-Za-z0-9\-\_]{1,63}$))', message="Enter a valid hostname. Full domain name may be 1-253 characters, each hostname 1-63 characters (including suffixed dot), and valid characters for hostnames are A-Z, a-z, 0-9, hyphen (-), and underscore (_)")
    name = models.CharField(max_length=200, validators=[hostname_validchars])

    def getHost(self):
        return self.generic_host

    def __str__(self):
        return self.name

    def validate(self):
        validname = re.compile('(?=^.{1,253}$)(?=(^([A-Za-z0-9\-\_]{1,62}\.)*[A-Za-z0-9\-\_]{1,63}$))')
        if not validname.match(self.name):
            return "Enter a valid hostname. Full domain name may be 1-253 characters, each hostname 1-63 characters (including suffixed dot), and valid characters for hostnames are A-Z, a-z, 0-9, hyphen (-), and underscore (_)"
        else:
            return None


# Host template
class GenericHost(models.Model):
    id = models.AutoField(primary_key=True)
    profile = models.ForeignKey(HostProfile, on_delete=models.DO_NOTHING)
    resource = models.OneToOneField(GenericResource, related_name='generic_host', on_delete=models.DO_NOTHING)

    def __str__(self):
        return self.resource.name


# Physical, actual resources
class ResourceBundle(models.Model):
    id = models.AutoField(primary_key=True)
    template = models.ForeignKey(GenericResourceBundle, on_delete=models.DO_NOTHING)

    def __str__(self):
        return "instance of " + str(self.template)


# Networking


class GenericInterface(models.Model):
    id = models.AutoField(primary_key=True)
    vlans = models.ManyToManyField(Vlan)
    profile = models.ForeignKey(InterfaceProfile, on_delete=models.DO_NOTHING)
    host = models.ForeignKey(GenericHost, on_delete=models.DO_NOTHING, related_name='generic_interfaces')

    def __str__(self):
        return "type " + str(self.profile) + " on host " + str(self.host)


class Scenario(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name

class Installer(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    sup_scenarios = models.ManyToManyField(Scenario, blank=True)

    def __str__(self):
        return self.name

class Opsys(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    sup_installers = models.ManyToManyField(Installer, blank=True)

    def __str__(self):
        return self.name

class ConfigBundle(models.Model):
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE) #consider setting to root user?
    name = models.CharField(max_length=200, unique=True)
    description = models.CharField(max_length=1000, default="")
    bundle = models.ForeignKey(GenericResourceBundle, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class OPNFVConfig(models.Model):
    id = models.AutoField(primary_key=True)
    installer = models.ForeignKey(Installer, on_delete=models.CASCADE)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    bundle = models.ForeignKey(ConfigBundle, related_name="opnfv_config", on_delete=models.CASCADE)

    def __str__(self):
        return "OPNFV job with " + str(self.installer) + " and " + str(self.scenario)

class OPNFVRole(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    description = models.TextField()

    def __str__(self):
        return self.name

class Image(models.Model):
    """
    model for representing OS images / snapshots of hosts
    """
    id = models.AutoField(primary_key=True)
    lab_id = models.IntegerField()  # ID the lab who holds this image knows
    from_lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    public = models.BooleanField(default=True)
    host_type = models.ForeignKey(HostProfile, on_delete=models.CASCADE) #may need to change to models.SET() once images are transferrable between compatible host types
    description = models.TextField()

    def __str__(self):
        return self.name

class HostConfiguration(models.Model):
    """
    model to represent a complete configuration for a single
    physical host
    """
    id = models.AutoField(primary_key=True)
    host = models.ForeignKey(GenericHost, related_name="configuration", on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.PROTECT)
    bundle = models.ForeignKey(ConfigBundle, related_name="hostConfigurations", null=True, on_delete=models.CASCADE)
    opnfvRole = models.ForeignKey(OPNFVRole, on_delete=models.PROTECT) #need protocol for phasing out a role if we are going to allow that to happen

    def __str__(self):
        return "config with " + str(self.host) + " and image " + str(self.image)


# Concrete host, actual machine in a lab
class Host(models.Model):
    id = models.AutoField(primary_key=True)
    template = models.ForeignKey(GenericHost, on_delete=models.SET_NULL, null=True)
    booked = models.BooleanField(default=False)
    name = models.CharField(max_length=200, unique=True)
    bundle = models.ForeignKey(ResourceBundle, related_name='hosts', on_delete=models.SET_NULL, null=True)
    config = models.ForeignKey(HostConfiguration, null=True, related_name="configuration", on_delete=models.SET_NULL)
    labid = models.CharField(max_length=200, default="default_id")
    profile = models.ForeignKey(HostProfile, on_delete=models.CASCADE)
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    working = models.BooleanField(default=True)
    vendor = models.CharField(max_length=100, default="unknown")
    model = models.CharField(max_length=150, default="unknown")

    def __str__(self):
        return self.name


class Interface(models.Model):
    id = models.AutoField(primary_key=True)
    mac_address = models.CharField(max_length=17)
    bus_address = models.CharField(max_length=50)
    name = models.CharField(max_length=100, default="eth0")
    config = models.ManyToManyField(Vlan)
    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='interfaces')

    def __str__(self):
        return self.mac_address + " on host " + str(self.host)
