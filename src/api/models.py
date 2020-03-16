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
from django.http import HttpResponseNotFound
from django.urls import reverse
from django.utils import timezone

import json
import uuid

from booking.models import Booking
from resource_inventory.models import (
    Lab,
    ResourceProfile,
    Image,
    Interface,
    ResourceOPNFVConfig,
    RemoteInfo,
    OPNFVConfig,
    ConfigState,
    ResourceQuery
)
from resource_inventory.idf_templater import IDFTemplater
from resource_inventory.pdf_templater import PDFTemplater
from account.models import Downtime
from dashboard.utils import AbstractModelQuery


class JobStatus(object):
    """
    A poor man's enum for a job's status.

    A job is NEW if it has not been started or recognized by the Lab
    A job is CURRENT if it has been started by the lab but it is not yet completed
    a job is DONE if all the tasks are complete and the booking is ready to use
    """

    NEW = 0
    CURRENT = 100
    DONE = 200
    ERROR = 300


class LabManagerTracker(object):

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


class LabManager(object):
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

    def update_host_remote_info(self, data, res_id):
        resource = ResourceQuery.filter(labid=res_id, lab=self.lab)
        if len(resource) != 1:
            return HttpResponseNotFound("Could not find single host with id " + str(res_id))
        resource = resource[0]
        info = {}
        try:
            info['address'] = data['address']
            info['mac_address'] = data['mac_address']
            info['password'] = data['password']
            info['user'] = data['user']
            info['type'] = data['type']
            info['versions'] = json.dumps(data['versions'])
        except Exception as e:
            return {"error": "invalid arguement: " + str(e)}
        remote_info = resource.remote_management
        if "default" in remote_info.mac_address:
            remote_info = RemoteInfo()
        remote_info.address = info['address']
        remote_info.mac_address = info['mac_address']
        remote_info.password = info['password']
        remote_info.user = info['user']
        remote_info.type = info['type']
        remote_info.versions = info['versions']
        remote_info.save()
        resource.remote_management = remote_info
        resource.save()
        booking = Booking.objects.get(resource=resource.bundle)
        self.update_xdf(booking)
        return {"status": "success"}

    def update_xdf(self, booking):
        booking.pdf = PDFTemplater.makePDF(booking)
        booking.idf = IDFTemplater().makeIDF(booking)
        booking.save()

    def get_pdf(self, booking_id):
        booking = get_object_or_404(Booking, pk=booking_id, lab=self.lab)
        return booking.pdf

    def get_idf(self, booking_id):
        booking = get_object_or_404(Booking, pk=booking_id, lab=self.lab)
        return booking.idf

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

    def get_inventory(self):
        inventory = {}
        resources = ResourceQuery.filter(lab=self.lab)
        images = Image.objects.filter(from_lab=self.lab)
        profiles = ResourceProfile.objects.filter(labs=self.lab)
        inventory['resources'] = self.serialize_resources(resources)
        inventory['images'] = self.serialize_images(images)
        inventory['host_types'] = self.serialize_host_profiles(profiles)
        return inventory

    def get_host(self, hostname):
        resource = ResourceQuery.filter(labid=hostname, lab=self.lab)
        if len(resource) != 1:
            return HttpResponseNotFound("Could not find single host with id " + str(hostname))
        resource = resource[0]
        return {
            "booked": resource.booked,
            "working": resource.working,
            "type": resource.profile.name
        }

    def update_host(self, hostname, data):
        resource = ResourceQuery.filter(labid=hostname, lab=self.lab)
        if len(resource) != 1:
            return HttpResponseNotFound("Could not find single host with id " + str(hostname))
        resource = resource[0]
        if "working" in data:
            working = data['working'] == "true"
            resource.working = working
        resource.save()
        return self.get_host(hostname)

    def get_status(self):
        return {"status": self.lab.status}

    def set_status(self, payload):
        {}

    def get_current_jobs(self):
        jobs = Job.objects.filter(booking__lab=self.lab)

        return self.serialize_jobs(jobs, status=JobStatus.CURRENT)

    def get_new_jobs(self):
        jobs = Job.objects.filter(booking__lab=self.lab)

        return self.serialize_jobs(jobs, status=JobStatus.NEW)

    def get_done_jobs(self):
        jobs = Job.objects.filter(booking__lab=self.lab)

        return self.serialize_jobs(jobs, status=JobStatus.DONE)

    def get_job(self, jobid):
        return Job.objects.get(pk=jobid).to_dict()

    def update_job(self, jobid, data):
        {}

    def serialize_jobs(self, jobs, status=JobStatus.NEW):
        job_ser = []
        for job in jobs:
            jsonized_job = job.get_delta(status)
            if len(jsonized_job['payload']) < 1:
                continue
            job_ser.append(jsonized_job)

        return job_ser

    def serialize_resources(self, resources):
        # TODO: rewrite for Resource model
        host_ser = []
        for res in resources:
            r = {
                'interfaces': [],
                'hostname': res.name,
                'host_type': res.profile.name
            }
            for iface in res.get_interfaces():
                r['interfaces'].append({
                    'mac': iface.mac_address,
                    'busaddr': iface.bus_address,
                    'name': iface.name,
                    'switchport': {"switch_name": iface.switch_name, "port_name": iface.port_name}
                })
        return host_ser

    def serialize_images(self, images):
        images_ser = []
        for image in images:
            images_ser.append(
                {
                    "name": image.name,
                    "lab_id": image.lab_id,
                    "dashboard_id": image.id
                }
            )
        return images_ser

    def serialize_resource_profiles(self, profiles):
        profile_ser = []
        for profile in profiles:
            p = {}
            p['cpu'] = {
                "cores": profile.cpuprofile.first().cores,
                "arch": profile.cpuprofile.first().architecture,
                "cpus": profile.cpuprofile.first().cpus,
            }
            p['disks'] = []
            for disk in profile.storageprofile.all():
                d = {
                    "size": disk.size,
                    "type": disk.media_type,
                    "name": disk.name
                }
                p['disks'].append(d)
            p['description'] = profile.description
            p['interfaces'] = []
            for iface in profile.interfaceprofile.all():
                p['interfaces'].append(
                    {
                        "speed": iface.speed,
                        "name": iface.name
                    }
                )

            p['ram'] = {"amount": profile.ramprofile.first().amount}
            p['name'] = profile.name
            profile_ser.append(p)
        return profile_ser


class Job(models.Model):
    """
    A Job to be performed by the Lab.

    The API uses Jobs and Tasks to communicate actions that need to be taken to the Lab
    that is hosting a booking. A booking from a user has an associated Job which tells
    the lab how to configure the hardware, networking, etc to fulfill the booking
    for the user.
    This is the class that is serialized and put into the api
    """

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, null=True)
    status = models.IntegerField(default=JobStatus.NEW)
    complete = models.BooleanField(default=False)

    def to_dict(self):
        d = {}
        for relation in self.get_tasklist():
            if relation.job_key not in d:
                d[relation.job_key] = {}
            d[relation.job_key][relation.task_id] = relation.config.to_dict()

        return {"id": self.id, "payload": d}

    def get_tasklist(self, status="all"):
        if status == "all":
            return JobTaskQuery.filter(job=self, status=status)
        return JobTaskQuery.filter(job=self)

    def is_fulfilled(self):
        """
        If a job has been completed by the lab.

        This method should return true if all of the job's tasks are done,
        and false otherwise
        """
        my_tasks = self.get_tasklist()
        for task in my_tasks:
            if task.status != JobStatus.DONE:
                return False
        return True

    def get_delta(self, status):
        d = {}
        for relation in self.get_tasklist(status=status):
            if relation.job_key not in d:
                d[relation.job_key] = {}
            d[relation.job_key][relation.task_id] = relation.config.get_delta()

        return {"id": self.id, "payload": d}

    def to_json(self):
        return json.dumps(self.to_dict())


class TaskConfig(models.Model):
    state = models.IntegerField(default=ConfigState.CLEAN)

    keys = set()  # TODO: This needs to be an instance variable, not a class variable
    delta_keys_list = models.CharField(max_length=200, default="[]")

    @property
    def delta_keys(self):
        return list(set(json.loads(self.delta_keys_list)))

    @delta_keys.setter
    def delta_keys(self, keylist):
        self.delta_keys_list = json.dumps(keylist)

    def to_dict(self):
        raise NotImplementedError

    def get_delta(self):
        raise NotImplementedError

    def format_delta(self, config, token):
        delta = {k: config[k] for k in self.delta_keys}
        delta['lab_token'] = token
        return delta

    def to_json(self):
        return json.dumps(self.to_dict())

    def clear_delta(self):
        self.delta_keys = []

    def set(self, *args):
        dkeys = self.delta_keys
        for arg in args:
            if arg in self.keys:
                dkeys.append(arg)
        self.delta_keys = dkeys


class BridgeConfig(models.Model):
    """Displays mapping between jumphost interfaces and bridges."""

    interfaces = models.ManyToManyField(Interface)
    opnfv_config = models.ForeignKey(OPNFVConfig, on_delete=models.CASCADE)

    def to_dict(self):
        d = {}
        hid = self.interfaces.first().host.labid
        d[hid] = {}
        for interface in self.interfaces.all():
            d[hid][interface.mac_address] = []
            for vlan in interface.config.all():
                network_role = self.opnfv_model.networks().filter(network=vlan.network)
                bridge = IDFTemplater.bridge_names[network_role.name]
                br_config = {
                    "vlan_id": vlan.vlan_id,
                    "tagged": vlan.tagged,
                    "bridge": bridge
                }
                d[hid][interface.mac_address].append(br_config)
        return d

    def to_json(self):
        return json.dumps(self.to_dict())


class OpnfvApiConfig(models.Model):

    installer = models.CharField(max_length=200)
    scenario = models.CharField(max_length=300)
    roles = models.ManyToManyField(ResourceOPNFVConfig)
    # pdf and idf are url endpoints, not the actual file
    pdf = models.CharField(max_length=100)
    idf = models.CharField(max_length=100)
    bridge_config = models.OneToOneField(BridgeConfig, on_delete=models.CASCADE, null=True)
    delta = models.TextField()
    opnfv_config = models.ForeignKey(OPNFVConfig, null=True, on_delete=models.SET_NULL)

    def to_dict(self):
        d = {}
        if not self.opnfv_config:
            return d
        if self.installer:
            d['installer'] = self.installer
        if self.scenario:
            d['scenario'] = self.scenario
        if self.pdf:
            d['pdf'] = self.pdf
        if self.idf:
            d['idf'] = self.idf
        if self.bridge_config:
            d['bridged_interfaces'] = self.bridge_config.to_dict()

        hosts = self.roles.all()
        if hosts.exists():
            d['roles'] = []
            for host in hosts:
                d['roles'].append({
                    host.labid: self.opnfv_config.host_opnfv_config.get(
                        host_config__pk=host.config.pk
                    ).role.name
                })

        return d

    def to_json(self):
        return json.dumps(self.to_dict())

    def set_installer(self, installer):
        self.installer = installer
        d = json.loads(self.delta)
        d['installer'] = installer
        self.delta = json.dumps(d)

    def set_scenario(self, scenario):
        self.scenario = scenario
        d = json.loads(self.delta)
        d['scenario'] = scenario
        self.delta = json.dumps(d)

    def set_xdf(self, booking, update_delta=True):
        kwargs = {'lab_name': booking.lab.name, 'booking_id': booking.id}
        self.pdf = reverse('get-pdf', kwargs=kwargs)
        self.idf = reverse('get-idf', kwargs=kwargs)
        if update_delta:
            d = json.loads(self.delta)
            d['pdf'] = self.pdf
            d['idf'] = self.idf
            self.delta = json.dumps(d)

    def add_role(self, host):
        self.roles.add(host)
        d = json.loads(self.delta)
        if 'role' not in d:
            d['role'] = []
        d['roles'].append({host.labid: host.config.opnfvRole.name})
        self.delta = json.dumps(d)

    def clear_delta(self):
        self.delta = '{}'

    def get_delta(self):
        if not self.delta:
            self.delta = self.to_json()
            self.save()
        return json.loads(self.delta)


class AccessConfig(TaskConfig):
    access_type = models.CharField(max_length=50)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    revoke = models.BooleanField(default=False)
    context = models.TextField(default="")
    delta = models.TextField(default="{}")

    def to_dict(self):
        d = {}
        d['access_type'] = self.access_type
        d['user'] = self.user.id
        d['revoke'] = self.revoke
        try:
            d['context'] = json.loads(self.context)
        except Exception:
            pass
        return d

    def get_delta(self):
        if not self.delta:
            self.delta = self.to_json()
            self.save()
        d = json.loads(self.delta)
        d["lab_token"] = self.accessrelation.lab_token

        return d

    def to_json(self):
        return json.dumps(self.to_dict())

    def clear_delta(self):
        d = {}
        d["lab_token"] = self.accessrelation.lab_token
        self.delta = json.dumps(d)

    def set_access_type(self, access_type):
        self.access_type = access_type
        d = json.loads(self.delta)
        d['access_type'] = access_type
        self.delta = json.dumps(d)

    def set_user(self, user):
        self.user = user
        d = json.loads(self.delta)
        d['user'] = self.user.id
        self.delta = json.dumps(d)

    def set_revoke(self, revoke):
        self.revoke = revoke
        d = json.loads(self.delta)
        d['revoke'] = revoke
        self.delta = json.dumps(d)

    def set_context(self, context):
        self.context = json.dumps(context)
        d = json.loads(self.delta)
        d['context'] = context
        self.delta = json.dumps(d)


class SoftwareConfig(TaskConfig):
    """Handles software installations, such as OPNFV or ONAP."""

    opnfv = models.ForeignKey(OpnfvApiConfig, on_delete=models.CASCADE)

    def to_dict(self):
        d = {}
        if self.opnfv:
            d['opnfv'] = self.opnfv.to_dict()

        d["lab_token"] = self.softwarerelation.lab_token
        self.delta = json.dumps(d)

        return d

    def get_delta(self):
        d = {}
        d['opnfv'] = self.opnfv.get_delta()
        d['lab_token'] = self.softwarerelation.lab_token

        return d

    def clear_delta(self):
        self.opnfv.clear_delta()

    def to_json(self):
        return json.dumps(self.to_dict())


class HardwareConfig(TaskConfig):
    """Describes the desired configuration of the hardware."""

    image = models.CharField(max_length=100, default="defimage")
    power = models.CharField(max_length=100, default="off")
    hostname = models.CharField(max_length=100, default="hostname")
    ipmi_create = models.BooleanField(default=False)
    delta = models.TextField()

    keys = set(["id", "image", "power", "hostname", "ipmi_create"])

    def get_delta(self):
        return self.format_delta(
            self.hosthardwarerelation.host.get_configuration(self.state),
            self.hosthardwarerelation.lab_token)


class NetworkConfig(TaskConfig):
    """Handles network configuration."""

    interfaces = models.ManyToManyField(Interface)
    delta = models.TextField()

    def to_dict(self):
        d = {}
        hid = self.hostnetworkrelation.host.labid
        d[hid] = {}
        for interface in self.interfaces.all():
            d[hid][interface.mac_address] = []
            for vlan in interface.config.all():
                # TODO: should this come from the interface?
                # e.g. will different interfaces for different resources need different configs?
                d[hid][interface.mac_address].append({"vlan_id": vlan.vlan_id, "tagged": vlan.tagged})

        return d

    def to_json(self):
        return json.dumps(self.to_dict())

    def get_delta(self):
        if not self.delta:
            self.delta = self.to_json()
            self.save()
        d = json.loads(self.delta)
        d['lab_token'] = self.hostnetworkrelation.lab_token
        return d

    def clear_delta(self):
        self.delta = json.dumps(self.to_dict())
        self.save()

    def add_interface(self, interface):
        self.interfaces.add(interface)
        d = json.loads(self.delta)
        hid = self.hostnetworkrelation.host.labid
        if hid not in d:
            d[hid] = {}
        d[hid][interface.mac_address] = []
        for vlan in interface.config.all():
            d[hid][interface.mac_address].append({"vlan_id": vlan.vlan_id, "tagged": vlan.tagged})
        self.delta = json.dumps(d)


class SnapshotConfig(TaskConfig):

    resource_id = models.CharField(max_length=200, default="default_id")
    image = models.IntegerField(null=True)
    dashboard_id = models.IntegerField()
    delta = models.TextField(default="{}")

    def to_dict(self):
        d = {}
        if self.host:
            d['host'] = self.host.labid
        if self.image:
            d['image'] = self.image
        d['dashboard_id'] = self.dashboard_id
        return d

    def to_json(self):
        return json.dumps(self.to_dict())

    def get_delta(self):
        if not self.delta:
            self.delta = self.to_json()
            self.save()

        d = json.loads(self.delta)
        return d

    def clear_delta(self):
        self.delta = json.dumps(self.to_dict())
        self.save()

    def set_host(self, host):
        self.host = host
        d = json.loads(self.delta)
        d['host'] = host.labid
        self.delta = json.dumps(d)

    def set_image(self, image):
        self.image = image
        d = json.loads(self.delta)
        d['image'] = self.image
        self.delta = json.dumps(d)

    def clear_image(self):
        self.image = None
        d = json.loads(self.delta)
        d.pop("image", None)
        self.delta = json.dumps(d)

    def set_dashboard_id(self, dash):
        self.dashboard_id = dash
        d = json.loads(self.delta)
        d['dashboard_id'] = self.dashboard_id
        self.delta = json.dumps(d)

    def save(self, *args, **kwargs):
        if len(ResourceQuery.filter(labid=self.resource_id)) != 1:
            raise ValidationError("resource_id " + str(self.resource_id) + " does not refer to a single resource")
        super().save(*args, **kwargs)


def get_task(task_id):
    for taskclass in [AccessRelation, SoftwareRelation, HostHardwareRelation, HostNetworkRelation, SnapshotRelation]:
        try:
            ret = taskclass.objects.get(task_id=task_id)
            return ret
        except taskclass.DoesNotExist:
            pass
    from django.core.exceptions import ObjectDoesNotExist
    raise ObjectDoesNotExist("Could not find matching TaskRelation instance")


def get_task_uuid():
    return str(uuid.uuid4())


class TaskRelation(models.Model):
    """
    Relates a Job to a TaskConfig.

    superclass that relates a Job to tasks anc maintains information
    like status and messages from the lab
    """

    status = models.IntegerField(default=JobStatus.NEW)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    config = models.OneToOneField(TaskConfig, on_delete=models.CASCADE)
    task_id = models.CharField(default=get_task_uuid, max_length=37)
    lab_token = models.CharField(default="null", max_length=50)
    message = models.TextField(default="")

    job_key = None

    def delete(self, *args, **kwargs):
        self.config.delete()
        return super(self.__class__, self).delete(*args, **kwargs)

    def type_str(self):
        return "Generic Task"

    class Meta:
        abstract = True


class AccessRelation(TaskRelation):
    config = models.OneToOneField(AccessConfig, on_delete=models.CASCADE)
    job_key = "access"

    def type_str(self):
        return "Access Task"

    def delete(self, *args, **kwargs):
        self.config.delete()
        return super(self.__class__, self).delete(*args, **kwargs)


class SoftwareRelation(TaskRelation):
    config = models.OneToOneField(SoftwareConfig, on_delete=models.CASCADE)
    job_key = "software"

    def type_str(self):
        return "Software Configuration Task"

    def delete(self, *args, **kwargs):
        self.config.delete()
        return super(self.__class__, self).delete(*args, **kwargs)


class HostHardwareRelation(TaskRelation):
    resource_id = models.CharField(max_length=200, default="default_id")
    config = models.OneToOneField(HardwareConfig, on_delete=models.CASCADE)
    job_key = "hardware"

    def type_str(self):
        return "Hardware Configuration Task"

    def get_delta(self):
        return self.config.to_dict()

    def delete(self, *args, **kwargs):
        self.config.delete()
        return super(self.__class__, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        if len(ResourceQuery.filter(labid=self.resource_id)) != 1:
            raise ValidationError("resource_id " + str(self.resource_id) + " does not refer to a single resource")
        super().save(*args, **kwargs)


class HostNetworkRelation(TaskRelation):
    resource_id = models.CharField(max_length=200, default="default_id")
    config = models.OneToOneField(NetworkConfig, on_delete=models.CASCADE)
    job_key = "network"

    def type_str(self):
        return "Network Configuration Task"

    def delete(self, *args, **kwargs):
        self.config.delete()
        return super(self.__class__, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        if len(ResourceQuery.filter(labid=self.resource_id)) != 1:
            raise ValidationError("resource_id " + str(self.resource_id) + " does not refer to a single resource")
        super().save(*args, **kwargs)


class SnapshotRelation(TaskRelation):
    snapshot = models.ForeignKey(Image, on_delete=models.CASCADE)
    config = models.OneToOneField(SnapshotConfig, on_delete=models.CASCADE)
    job_key = "snapshot"

    def type_str(self):
        return "Snapshot Task"

    def get_delta(self):
        return self.config.to_dict()

    def delete(self, *args, **kwargs):
        self.config.delete()
        return super(self.__class__, self).delete(*args, **kwargs)


class JobFactory(object):
    """This class creates all the API models (jobs, tasks, etc) needed to fulfill a booking."""

    @classmethod
    def reimageHost(cls, new_image, booking, host):
        """Modify an existing job to reimage the given host."""
        job = Job.objects.get(booking=booking)
        # make hardware task new
        hardware_relation = HostHardwareRelation.objects.get(host=host, job=job)
        hardware_relation.config.set_image(new_image.lab_id)
        hardware_relation.config.save()
        hardware_relation.status = JobStatus.NEW

        # re-apply networking after host is reset
        net_relation = HostNetworkRelation.objects.get(host=host, job=job)
        net_relation.status = JobStatus.NEW

        # re-apply ssh access after host is reset
        for relation in AccessRelation.objects.filter(job=job, config__access_type="ssh"):
            relation.status = JobStatus.NEW
            relation.save()

        hardware_relation.save()
        net_relation.save()

    @classmethod
    def makeSnapshotTask(cls, image, booking, host):
        relation = SnapshotRelation()
        job = Job.objects.get(booking=booking)
        config = SnapshotConfig.objects.create(dashboard_id=image.id)

        relation.job = job
        relation.config = config
        relation.config.save()
        relation.config = relation.config
        relation.snapshot = image
        relation.save()

        config.clear_delta()
        config.set_host(host)
        config.save()

    @classmethod
    def makeCompleteJob(cls, booking):
        """Create everything that is needed to fulfill the given booking."""
        resources = booking.resource.get_resources()
        job = None
        try:
            job = Job.objects.get(booking=booking)
        except Exception:
            job = Job.objects.create(status=JobStatus.NEW, booking=booking)
        cls.makeHardwareConfigs(
            resources=resources,
            job=job
        )
        cls.makeNetworkConfigs(
            resources=resources,
            job=job
        )
        cls.makeSoftware(
            booking=booking,
            job=job
        )
        all_users = list(booking.collaborators.all())
        all_users.append(booking.owner)
        cls.makeAccessConfig(
            users=all_users,
            access_type="vpn",
            revoke=False,
            job=job
        )
        for user in all_users:
            try:
                cls.makeAccessConfig(
                    users=[user],
                    access_type="ssh",
                    revoke=False,
                    job=job,
                    context={
                        "key": user.userprofile.ssh_public_key.open().read().decode(encoding="UTF-8"),
                        "hosts": [r.labid for r in resources]
                    }
                )
            except Exception:
                continue

    @classmethod
    def makeHardwareConfigs(cls, resources=[], job=Job()):
        """
        Create and save HardwareConfig.

        Helper function to create the tasks related to
        configuring the hardware
        """
        for res in resources:
            hardware_config = None
            try:
                hardware_config = HardwareConfig.objects.get(relation__host=res)
            except Exception:
                hardware_config = HardwareConfig()

            relation = HostHardwareRelation()
            relation.resource_id = res.labid
            relation.job = job
            relation.config = hardware_config
            relation.config.save()
            relation.config = relation.config
            relation.save()

            hardware_config.set("image", "hostname", "power", "ipmi_create")
            hardware_config.save()

    @classmethod
    def makeAccessConfig(cls, users, access_type, revoke=False, job=Job(), context=False):
        """
        Create and save AccessConfig.

        Helper function to create the tasks related to
        configuring the VPN, SSH, etc access for users
        """
        for user in users:
            relation = AccessRelation()
            relation.job = job
            config = AccessConfig()
            config.access_type = access_type
            config.user = user
            config.save()
            relation.config = config
            relation.save()
            config.clear_delta()
            if context:
                config.set_context(context)
            config.set_access_type(access_type)
            config.set_revoke(revoke)
            config.set_user(user)
            config.save()

    @classmethod
    def makeNetworkConfigs(cls, resources=[], job=Job()):
        """
        Create and save NetworkConfig.

        Helper function to create the tasks related to
        configuring the networking
        """
        for res in resources:
            network_config = None
            try:
                network_config = NetworkConfig.objects.get(relation__host=res)
            except Exception:
                network_config = NetworkConfig.objects.create()

            relation = HostNetworkRelation()
            relation.resource_id = res.labid
            relation.job = job
            network_config.save()
            relation.config = network_config
            relation.save()
            network_config.clear_delta()

            # TODO: use get_interfaces() on resource
            for interface in res.interfaces.all():
                network_config.add_interface(interface)
            network_config.save()

    @classmethod
    def make_bridge_config(cls, booking):
        if booking.resource.hosts.count() < 2:
            return None
        try:
            jumphost_config = ResourceOPNFVConfig.objects.filter(
                role__name__iexact="jumphost"
            )
            jumphost = ResourceQuery.filter(
                bundle=booking.resource,
                config=jumphost_config.resource_config
            )[0]
        except Exception:
            return None
        br_config = BridgeConfig.objects.create(opnfv_config=booking.opnfv_config)
        for iface in jumphost.interfaces.all():
            br_config.interfaces.add(iface)
        return br_config

    @classmethod
    def makeSoftware(cls, booking=None, job=Job()):
        """
        Create and save SoftwareConfig.

        Helper function to create the tasks related to
        configuring the desired software, e.g. an OPNFV deployment
        """
        if not booking.opnfv_config:
            return None

        opnfv_api_config = OpnfvApiConfig.objects.create(
            opnfv_config=booking.opnfv_config,
            installer=booking.opnfv_config.installer.name,
            scenario=booking.opnfv_config.scenario.name,
            bridge_config=cls.make_bridge_config(booking)
        )

        opnfv_api_config.set_xdf(booking, False)
        opnfv_api_config.save()

        for host in booking.resource.hosts.all():
            opnfv_api_config.roles.add(host)
        software_config = SoftwareConfig.objects.create(opnfv=opnfv_api_config)
        software_relation = SoftwareRelation.objects.create(job=job, config=software_config)
        return software_relation


JOB_TASK_CLASSLIST = [
    HostHardwareRelation,
    AccessRelation,
    HostNetworkRelation,
    SoftwareRelation,
    SnapshotRelation
]


class JobTaskQuery(AbstractModelQuery):
    model_list = JOB_TASK_CLASSLIST
