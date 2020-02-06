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
        validname = re.compile(r"^[A-Za-z0-9\-\_\.\/\, ]+$")
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
    host = models.ForeignKey(HostProfile, on_delete=models.CASCADE, related_name='interfaceprofile')
    nic_type = models.CharField(
        max_length=50,
        choices=[
            ("onboard", "onboard"),
            ("pcie", "pcie")
        ],
        default="onboard"
    )

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
    host = models.ForeignKey(HostProfile, on_delete=models.CASCADE, related_name='storageprofile')
    rotation = models.IntegerField(default=0)
    interface = models.CharField(
        max_length=50,
        choices=[
            ("sata", "sata"),
            ("sas", "sas"),
            ("ssd", "ssd"),
            ("nvme", "nvme"),
            ("scsi", "scsi"),
            ("iscsi", "iscsi"),
        ],
        default="sata"
    )

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
    host = models.ForeignKey(HostProfile, on_delete=models.CASCADE, related_name='cpuprofile')
    cflags = models.TextField(null=True)

    def __str__(self):
        return str(self.architecture) + " " + str(self.cpus) + "S" + str(self.cores) + " C for " + str(self.host)


class RamProfile(models.Model):
    id = models.AutoField(primary_key=True)
    amount = models.IntegerField()
    channels = models.IntegerField()
    host = models.ForeignKey(HostProfile, on_delete=models.CASCADE, related_name='ramprofile')

    def __str__(self):
        return str(self.amount) + "G for " + str(self.host)


class Resource(models.Model):
    class Meta:
        abstract = True

    def get_configuration(self, state):
        """
        Get configuration of Resource.

        Returns the desired configuration for this host as a
        JSON object as defined in the rest api spec.
        state is a ConfigState
        """
        raise NotImplementedError("Must implement in concrete Resource classes")

    def reserve(self):
        """Reserve this resource for its currently assigned booking."""
        raise NotImplementedError("Must implement in concrete Resource classes")

    def release(self):
        """Make this resource available again for new boookings."""
        raise NotImplementedError("Must implement in concrete Resource classes")


# Generic resource templates
class GenericResourceBundle(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=300, unique=True)
    xml = models.TextField()
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    lab = models.ForeignKey(Lab, null=True, on_delete=models.SET_NULL)
    description = models.CharField(max_length=1000, default="")
    public = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)

    def getResources(self):
        my_resources = []
        for genericResource in self.generic_resources.all():
            my_resources.append(genericResource.getResource())

        return my_resources

    def __str__(self):
        return self.name


class Network(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    bundle = models.ForeignKey(GenericResourceBundle, on_delete=models.CASCADE, related_name="networks")
    is_public = models.BooleanField()

    def __str__(self):
        return self.name


class PhysicalNetwork(Resource):
    vlan_id = models.IntegerField()
    generic_network = models.ForeignKey(Network, on_delete=models.CASCADE)

    def get_configuration(self, state):
        """
        Get the network configuration.

        Collects info about each attached network interface and vlan, etc
        """
        return {}

    def reserve(self):
        """Reserve vlan(s) associated with this network."""
        # vlan_manager = self.bundle.lab.vlan_manager
        return False

    def release(self):
        # vlan_manager = self.bundle.lab.vlan_manager
        return False


class NetworkConnection(models.Model):
    network = models.ForeignKey(Network, on_delete=models.CASCADE)
    vlan_is_tagged = models.BooleanField()


class Vlan(models.Model):
    id = models.AutoField(primary_key=True)
    vlan_id = models.IntegerField()
    tagged = models.BooleanField()
    public = models.BooleanField(default=False)
    network = models.ForeignKey(PhysicalNetwork, on_delete=models.DO_NOTHING, null=True)

    def __str__(self):
        return str(self.vlan_id) + ("_T" if self.tagged else "")


class ConfigState:
    NEW = 0
    RESET = 100
    CLEAN = 200


class GenericResource(models.Model):
    bundle = models.ForeignKey(GenericResourceBundle, related_name='generic_resources', on_delete=models.CASCADE)
    hostname_validchars = RegexValidator(regex=r'(?=^.{1,253}$)(?=(^([A-Za-z0-9\-\_]{1,62}\.)*[A-Za-z0-9\-\_]{1,63}$))', message="Enter a valid hostname. Full domain name may be 1-253 characters, each hostname 1-63 characters (including suffixed dot), and valid characters for hostnames are A-Z, a-z, 0-9, hyphen (-), and underscore (_)")
    name = models.CharField(max_length=200, validators=[hostname_validchars])

    def getResource(self):
        # TODO: This will have to be dealt with
        return self.generic_host

    def __str__(self):
        return self.name

    def validate(self):
        validname = re.compile(r'(?=^.{1,253}$)(?=(^([A-Za-z0-9\-\_]{1,62}\.)*[A-Za-z0-9\-\_]{1,63}$))')
        if not validname.match(self.name):
            return "Enter a valid hostname. Full domain name may be 1-253 characters, each hostname 1-63 characters (including suffixed dot), and valid characters for hostnames are A-Z, a-z, 0-9, hyphen (-), and underscore (_)"
        else:
            return None


# Host template
class GenericHost(models.Model):
    id = models.AutoField(primary_key=True)
    profile = models.ForeignKey(HostProfile, on_delete=models.CASCADE)
    resource = models.OneToOneField(GenericResource, related_name='generic_host', on_delete=models.CASCADE)

    def __str__(self):
        return self.resource.name


# Physical, actual resources
class ResourceBundle(Resource):
    template = models.ForeignKey(GenericResourceBundle, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        if self.template is None:
            return "Resource bundle " + str(self.id) + " with no template"
        return "instance of " + str(self.template)

    def get_host(self, role="Jumphost"):
        return Host.objects.filter(bundle=self, config__is_head_node=True).first()  # should only ever be one, but it is not an invariant in the models


class GenericInterface(models.Model):
    id = models.AutoField(primary_key=True)
    profile = models.ForeignKey(InterfaceProfile, on_delete=models.CASCADE)
    host = models.ForeignKey(GenericHost, on_delete=models.CASCADE, related_name='generic_interfaces')
    connections = models.ManyToManyField(NetworkConnection)

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


class NetworkRole(models.Model):
    name = models.CharField(max_length=100)
    network = models.ForeignKey(Network, on_delete=models.CASCADE)


class ConfigBundle(models.Model):
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, unique=True)
    description = models.CharField(max_length=1000, default="")
    bundle = models.ForeignKey(GenericResourceBundle, null=True, on_delete=models.CASCADE)
    public = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class OPNFVConfig(models.Model):
    id = models.AutoField(primary_key=True)
    installer = models.ForeignKey(Installer, on_delete=models.CASCADE)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    bundle = models.ForeignKey(ConfigBundle, related_name="opnfv_config", on_delete=models.CASCADE)
    networks = models.ManyToManyField(NetworkRole)
    name = models.CharField(max_length=300, blank=True, default="")
    description = models.CharField(max_length=600, blank=True, default="")

    def __str__(self):
        return "OPNFV job with " + str(self.installer) + " and " + str(self.scenario)


class OPNFVRole(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    description = models.TextField()

    def __str__(self):
        return self.name


class Image(models.Model):
    """Model for representing OS images / snapshots of hosts."""

    id = models.AutoField(primary_key=True)
    lab_id = models.IntegerField()  # ID the lab who holds this image knows
    from_lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    public = models.BooleanField(default=True)
    host_type = models.ForeignKey(HostProfile, on_delete=models.CASCADE)
    description = models.TextField()
    os = models.ForeignKey(Opsys, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    def in_use(self):
        return Host.objects.filter(booked=True, config__image=self).exists()


def get_sentinal_opnfv_role():
    return OPNFVRole.objects.get_or_create(name="deleted", description="Role was deleted.")


class HostConfiguration(models.Model):
    """Model to represent a complete configuration for a single physical host."""

    id = models.AutoField(primary_key=True)
    host = models.ForeignKey(GenericHost, related_name="configuration", on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.PROTECT)
    bundle = models.ForeignKey(ConfigBundle, related_name="hostConfigurations", null=True, on_delete=models.CASCADE)
    is_head_node = models.BooleanField(default=False)

    def __str__(self):
        return "config with " + str(self.host) + " and image " + str(self.image)


class HostOPNFVConfig(models.Model):
    role = models.ForeignKey(OPNFVRole, related_name="host_opnfv_configs", on_delete=models.CASCADE)
    host_config = models.ForeignKey(HostConfiguration, related_name="host_opnfv_config", on_delete=models.CASCADE)
    opnfv_config = models.ForeignKey(OPNFVConfig, related_name="host_opnfv_config", on_delete=models.CASCADE)


class RemoteInfo(models.Model):
    address = models.CharField(max_length=15)
    mac_address = models.CharField(max_length=17)
    password = models.CharField(max_length=100)
    user = models.CharField(max_length=100)
    management_type = models.CharField(max_length=50, default="ipmi")
    versions = models.CharField(max_length=100)  # json serialized list of floats


def get_default_remote_info():
    return RemoteInfo.objects.get_or_create(
        address="default",
        mac_address="default",
        password="default",
        user="default",
        management_type="default",
        versions="[default]"
    )[0].pk


# Concrete host, actual machine in a lab
class Host(Resource):
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
    remote_management = models.ForeignKey(RemoteInfo, default=get_default_remote_info, on_delete=models.SET(get_default_remote_info))

    def __str__(self):
        return self.name

    def get_configuration(self, state):
        ipmi = state == ConfigState.NEW
        power = "off" if state == ConfigState.CLEAN else "on"

        return {
            "id": self.labid,
            "image": self.config.image.lab_id,
            "hostname": self.template.resource.name,
            "power": power,
            "ipmi_create": str(ipmi)
        }


class Interface(models.Model):
    id = models.AutoField(primary_key=True)
    mac_address = models.CharField(max_length=17)
    bus_address = models.CharField(max_length=50)
    config = models.ManyToManyField(Vlan)
    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='interfaces')
    profile = models.ForeignKey(InterfaceProfile, on_delete=models.CASCADE)

    def __str__(self):
        return self.mac_address + " on host " + str(self.host)


class OPNFV_SETTINGS():
    """This is a static configuration class."""

    # all the required network types in PDF/IDF spec
    NETWORK_ROLES = ["public", "private", "admin", "mgmt"]
