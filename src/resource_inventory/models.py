##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
# Copyright (c) 2020 Sawyer Bergeron, Sean Smith, others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.contrib.auth.models import User

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
import traceback
import json

import re
from collections import Counter

from account.models import Lab
from dashboard.utils import AbstractModelQuery

"""
Profiles of resources hosted by labs.

These describe hardware attributes of the different Resources a lab hosts.
A single Resource subclass (e.g. Server) may have instances that point to different
Profile models (e.g. an x86 server profile and armv8 server profile.
"""


class ResourceProfile(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    architecture = models.CharField(max_length=50, choices=[
        ("x86_64", "x86_64"),
        ("aarch64", "aarch64")
    ])
    description = models.TextField()
    labs = models.ManyToManyField(Lab, related_name="resourceprofiles")

    def validate(self):
        validname = re.compile(r"^[A-Za-z0-9\-\_\.\/\, ]+$")
        if not validname.match(self.name):
            return "Invalid host profile name given. Name must only use A-Z, a-z, 0-9, hyphens, underscores, dots, commas, or spaces."
        else:
            return None

    def __str__(self):
        return self.name

    def get_resources(self, lab=None, working=True, unreserved=False):
        """
        Return a list of Resource objects which have this profile.

        If lab is provided, only resources at that lab will be returned.
        If working=True, will only return working hosts
        """
        resources = []
        query = Q(profile=self)
        if lab:
            query = query & Q(lab=lab)
        if working:
            query = query & Q(working=True)

        resources = ResourceQuery.filter(query)

        if unreserved:
            resources = [r for r in resources if not r.is_reserved()]

        return resources


class InterfaceProfile(models.Model):
    id = models.AutoField(primary_key=True)
    speed = models.IntegerField()
    name = models.CharField(max_length=100)
    host = models.ForeignKey(ResourceProfile, on_delete=models.CASCADE, related_name='interfaceprofile')
    nic_type = models.CharField(
        max_length=50,
        choices=[
            ("onboard", "onboard"),
            ("pcie", "pcie")
        ],
        default="onboard"
    )
    order = models.IntegerField(default=-1)

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
    host = models.ForeignKey(ResourceProfile, on_delete=models.CASCADE, related_name='storageprofile')
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
    host = models.ForeignKey(ResourceProfile, on_delete=models.CASCADE, related_name='cpuprofile')
    cflags = models.TextField(null=True, blank=True)

    def __str__(self):
        return str(self.architecture) + " " + str(self.cpus) + "S" + str(self.cores) + " C for " + str(self.host)


class RamProfile(models.Model):
    id = models.AutoField(primary_key=True)
    amount = models.IntegerField()
    channels = models.IntegerField()
    host = models.ForeignKey(ResourceProfile, on_delete=models.CASCADE, related_name='ramprofile')

    def __str__(self):
        return str(self.amount) + "G for " + str(self.host)


"""
Resource Models

These models represent actual hardware resources
with varying degrees of abstraction.
"""


class CloudInitFile(models.Model):
    text = models.TextField()

    # higher priority is applied later, so "on top" of existing files
    priority = models.IntegerField()
    generated = models.BooleanField(default=False)

    @classmethod
    def merge_strategy(cls):
        return [
            {'name': 'list', 'settings': ['append']},
            {'name': 'dict', 'settings': ['recurse_list', 'replace']},
        ]

    @classmethod
    def create(cls, text="", priority=0):
        return CloudInitFile.objects.create(priority=priority, text=text)


class ResourceTemplate(models.Model):
    """
    Models a "template" of a complete, configured collection of resources that can be booked.

    For example, this may represent a Pharos POD. This model is a template of the actual
    resources that will be booked. This model can be "instantiated" into real resource models
    across multiple different bookings.
    """

    # TODO: template might not be a good name because this is a collection of lots of configured resources
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=300)
    xml = models.TextField()
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    lab = models.ForeignKey(Lab, null=True, on_delete=models.SET_NULL, related_name="resourcetemplates")
    description = models.CharField(max_length=1000, default="")
    public = models.BooleanField(default=False)
    temporary = models.BooleanField(default=False)
    copy_of = models.ForeignKey("ResourceTemplate", blank=True, null=True, on_delete=models.SET_NULL)

    # if these fields are empty ("") then they are implicitly "every vlan",
    # otherwise we filter any allocations we try to instantiate against this list
    # they should be represented as a json list of integers
    private_vlan_pool = models.TextField(default="")
    public_vlan_pool = models.TextField(default="")

    def private_vlan_pool_set(self):
        if self.private_vlan_pool != "":
            return set(json.loads(self.private_vlan_pool))
        else:
            return None

    def public_vlan_pool_set(self):
        if self.private_vlan_pool != "":
            return set(json.loads(self.public_vlan_pool))
        else:
            return None

    def getConfigs(self):
        configs = self.resourceConfigurations.all()
        return list(configs)

    def get_required_resources(self):
        profiles = Counter([str(config.profile) for config in self.getConfigs()])
        return dict(profiles)

    def __str__(self):
        return self.name


class ResourceBundle(models.Model):
    """
    Collection of Resource objects.

    This is just a way of aggregating all the resources in a booking into a single model.
    """

    template = models.ForeignKey(ResourceTemplate, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        if self.template is None:
            return "Resource bundle " + str(self.id) + " with no template"
        return "instance of " + str(self.template)

    def get_resources(self):
        return ResourceQuery.filter(bundle=self)

    def get_resource_with_role(self, role):
        # TODO
        pass

    def release(self):
        for pn in PhysicalNetwork.objects.filter(bundle=self).all():
            try:
                pn.release()
            except Exception as e:
                print("Exception occurred while trying to release resource ", pn.vlan_id)
                print(e)
                traceback.print_exc()

        for resource in self.get_resources():
            try:
                resource.release()
            except Exception as e:
                print("Exception occurred while trying to release resource ", resource)
                print(e)
                traceback.print_exc()

    def get_template_name(self):
        if not self.template:
            return ""
        if not self.template.temporary:
            return self.template.name
        return self.template.copy_of.name


class ResourceConfiguration(models.Model):
    """Model to represent a complete configuration for a single physical Resource."""

    id = models.AutoField(primary_key=True)
    profile = models.ForeignKey(ResourceProfile, on_delete=models.CASCADE)
    image = models.ForeignKey("Image", on_delete=models.PROTECT)
    template = models.ForeignKey(ResourceTemplate, related_name="resourceConfigurations", null=True, on_delete=models.CASCADE)
    is_head_node = models.BooleanField(default=False)
    name = models.CharField(max_length=3000, default="opnfv_host")

    cloud_init_files = models.ManyToManyField(CloudInitFile, blank=True)

    def __str__(self):
        return str(self.name)

    def ci_file_list(self):
        return list(self.cloud_init_files.order_by("priority").all())


def get_default_remote_info():
    return RemoteInfo.objects.get_or_create(
        address="default",
        mac_address="default",
        password="default",
        user="default",
        management_type="default",
        versions="[default]"
    )[0].pk


class Resource(models.Model):
    """
    Super class for all hardware resource models.

    Defines methods that must be implemented and common database fields.
    Any new kind of Resource a lab wants to host (White box switch, traffic generator, etc)
    should inherit from this class and fulfill the functional interface
    """

    class Meta:
        abstract = True

    bundle = models.ForeignKey(ResourceBundle, on_delete=models.SET_NULL, blank=True, null=True)
    profile = models.ForeignKey(ResourceProfile, on_delete=models.CASCADE)
    config = models.ForeignKey(ResourceConfiguration, on_delete=models.SET_NULL, blank=True, null=True)
    working = models.BooleanField(default=True)
    vendor = models.CharField(max_length=100, default="unknown")
    model = models.CharField(max_length=150, default="unknown")
    interfaces = models.ManyToManyField("Interface")
    remote_management = models.ForeignKey("RemoteInfo", default=get_default_remote_info, on_delete=models.SET(get_default_remote_info))
    labid = models.CharField(max_length=200, default="default_id", unique=True)
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)

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

    def get_interfaces(self):
        """
        Return a list of interfaces on this resource.

        The ordering of interfaces should be consistent.
        """
        raise NotImplementedError("Must implement in concrete Resource classes")

    def is_reserved(self):
        """Return True if this Resource is reserved."""
        raise NotImplementedError("Must implement in concrete Resource classes")

    def same_instance(self, other):
        """Return True if this Resource is the same instance as other."""
        raise NotImplementedError("Must implement in concrete Resource classes")

    def save(self, *args, **kwargs):
        """Assert that labid is unique across all Resource models."""
        res = ResourceQuery.filter(labid=self.labid)
        if len(res) > 1:
            raise ValidationError("Too many resources with labid " + str(self.labid))

        if len(res) == 1:
            if not self.same_instance(res[0]):
                raise ValidationError("Too many resources with labid " + str(self.labid))
        super().save(*args, **kwargs)


class RemoteInfo(models.Model):
    address = models.CharField(max_length=15)
    mac_address = models.CharField(max_length=17)
    password = models.CharField(max_length=100)
    user = models.CharField(max_length=100)
    management_type = models.CharField(max_length=50, default="ipmi")
    versions = models.CharField(max_length=100)  # json serialized list of floats


class Server(Resource):
    """Resource subclass - a basic baremetal server."""

    booked = models.BooleanField(default=False)
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name

    def get_configuration(self, state):
        ipmi = state == ConfigState.NEW
        power = "off" if state == ConfigState.CLEAN else "on"
        image = self.config.image.lab_id if self.config else "unknown"

        return {
            "id": self.labid,
            "image": image,
            "hostname": self.config.name,
            "power": power,
            "ipmi_create": str(ipmi)
        }

    def get_interfaces(self):
        return list(self.interfaces.all().order_by('bus_address'))

    def release(self):
        self.bundle = None
        self.booked = False
        self.save()

    def reserve(self):
        self.booked = True
        self.save()

    def is_reserved(self):
        return self.booked

    def same_instance(self, other):
        return isinstance(other, Server) and other.name == self.name


def is_serializable(data):
    try:
        json.dumps(data)
        return True
    except Exception:
        return False


class Opsys(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    lab_id = models.CharField(max_length=100)
    obsolete = models.BooleanField(default=False)
    available = models.BooleanField(default=True)  # marked true by Cobbler if it exists there
    from_lab = models.ForeignKey(Lab, on_delete=models.CASCADE)

    indexes = [
        models.Index(fields=['cobbler_id'])
    ]

    def new_from_data(data):
        opsys = Opsys()
        opsys.update(data)
        return opsys

    def serialize(self):
        d = {}
        for field in vars(self):
            attr = getattr(self, field)
            if is_serializable(attr):
                d[field] = attr
        return d

    def update(self, data):
        for field in vars(self):
            if field in data:
                setattr(self, field, data[field] if data[field] else getattr(self, field))

    def __str__(self):
        return self.name


class Image(models.Model):
    """Model for representing OS images / snapshots of hosts."""

    id = models.AutoField(primary_key=True)
    from_lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    architecture = models.CharField(max_length=50, choices=[
        ("x86_64", "x86_64"),
        ("aarch64", "aarch64"),
        ("unknown", "unknown"),
    ])
    lab_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    public = models.BooleanField(default=True)
    description = models.TextField()
    os = models.ForeignKey(Opsys, null=True, on_delete=models.CASCADE)

    available = models.BooleanField(default=True)  # marked True by cobbler if it exists there
    obsolete = models.BooleanField(default=False)

    indexes = [
        models.Index(fields=['architecture']),
        models.Index(fields=['cobbler_id'])
    ]

    def __str__(self):
        return self.name

    def is_obsolete(self):
        return self.obsolete or self.os.obsolete

    def serialize(self):
        d = {}
        for field in vars(self):
            attr = getattr(self, field)
            if is_serializable(attr):
                d[field] = attr
        return d

    def update(self, data):
        for field in vars(self):
            if field in data:
                setattr(self, field, data[field] if data[field] else getattr(self, field))

    def new_from_data(data):
        img = Image()
        img.update(data)
        return img

    def in_use(self):
        for resource in ResourceQuery.filter(config__image=self):
            if resource.is_reserved():
                return True

        return False


"""
Networking configuration models
"""


class Network(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    bundle = models.ForeignKey(ResourceTemplate, on_delete=models.CASCADE, related_name="networks")
    is_public = models.BooleanField()

    def __str__(self):
        return self.name


class PhysicalNetwork(models.Model):
    vlan_id = models.IntegerField()
    generic_network = models.ForeignKey(Network, on_delete=models.CASCADE)
    bundle = models.ForeignKey(ResourceBundle, null=True, blank=True, on_delete=models.CASCADE)

    def get_configuration(self, state):
        """
        Get the network configuration.

        Collects info about each attached network interface and vlan, etc
        """
        return {}

    def reserve(self):
        """Reserve vlan(s) associated with this network."""
        return False

    def release(self):
        from booking.models import Booking

        booking = Booking.objects.get(resource=self.bundle)
        lab = booking.lab
        vlan_manager = lab.vlan_manager

        if self.generic_network.is_public:
            vlan_manager.release_public_vlan(self.vlan_id)
        else:
            vlan_manager.release_vlans([self.vlan_id])
        return False

    def __str__(self):
        return 'Physical Network for ' + self.generic_network.name


class NetworkConnection(models.Model):
    network = models.ForeignKey(Network, on_delete=models.CASCADE)
    vlan_is_tagged = models.BooleanField()

    def __str__(self):
        return 'Connection to ' + self.network.name


class Vlan(models.Model):
    id = models.AutoField(primary_key=True)
    vlan_id = models.IntegerField()
    tagged = models.BooleanField()
    public = models.BooleanField(default=False)
    network = models.ForeignKey(PhysicalNetwork, on_delete=models.DO_NOTHING, null=True)

    def __str__(self):
        return str(self.vlan_id) + ("_T" if self.tagged else "")


class InterfaceConfiguration(models.Model):
    id = models.AutoField(primary_key=True)
    profile = models.ForeignKey(InterfaceProfile, on_delete=models.CASCADE)
    resource_config = models.ForeignKey(ResourceConfiguration, on_delete=models.CASCADE, related_name='interface_configs')
    connections = models.ManyToManyField(NetworkConnection, blank=True)

    def __str__(self):
        return "type " + str(self.profile) + " on host " + str(self.resource_config)


"""
OPNFV / Software configuration models
"""


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


class NetworkRole(models.Model):
    name = models.CharField(max_length=100)
    network = models.ForeignKey(Network, on_delete=models.CASCADE)


def create_resource_ref_string(for_hosts: [str]) -> str:
    # need to sort the list, then do dump
    for_hosts.sort()

    return json.dumps(for_hosts)


class OPNFVConfig(models.Model):
    id = models.AutoField(primary_key=True)
    installer = models.ForeignKey(Installer, on_delete=models.CASCADE)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    template = models.ForeignKey(ResourceTemplate, related_name="opnfv_config", on_delete=models.CASCADE)
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


def get_sentinal_opnfv_role():
    return OPNFVRole.objects.get_or_create(name="deleted", description="Role was deleted.")


class ResourceOPNFVConfig(models.Model):
    role = models.ForeignKey(OPNFVRole, related_name="resource_opnfv_configs", on_delete=models.CASCADE)
    resource_config = models.ForeignKey(ResourceConfiguration, related_name="resource_opnfv_config", on_delete=models.CASCADE)
    opnfv_config = models.ForeignKey(OPNFVConfig, related_name="resource_opnfv_config", on_delete=models.CASCADE)


class Interface(models.Model):
    id = models.AutoField(primary_key=True)
    mac_address = models.CharField(max_length=17)
    bus_address = models.CharField(max_length=50)
    config = models.ManyToManyField(Vlan)
    acts_as = models.OneToOneField(InterfaceConfiguration, blank=True, null=True, on_delete=models.CASCADE)
    profile = models.ForeignKey(InterfaceProfile, on_delete=models.CASCADE)

    def __str__(self):
        return self.mac_address + " on host " + str(self.profile.host.name)

    def clean(self, *args, **kwargs):
        if self.acts_as and self.acts_as.profile != self.profile:
            raise ValidationError("Interface Configuration's Interface Profile does not match Interface Profile chosen for Interface.")
        super().clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


"""
Some Enums for dealing with global constants.
"""


class OPNFV_SETTINGS():
    """This is a static configuration class."""

    # all the required network types in PDF/IDF spec
    NETWORK_ROLES = ["public", "private", "admin", "mgmt"]


class ConfigState:
    NEW = 0
    RESET = 100
    CLEAN = 200


RESOURCE_TYPES = [Server]


class ResourceQuery(AbstractModelQuery):
    model_list = [Server]
