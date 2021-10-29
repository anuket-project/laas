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

from booking.models import Booking
from resource_inventory.models import (
    Lab,
    ResourceProfile,
    Image,
    Opsys,
    Interface,
    ResourceOPNFVConfig,
    RemoteInfo,
    OPNFVConfig,
    ConfigState,
    ResourceQuery,
    ResourceConfiguration,
    CloudInitFile
)
from resource_inventory.idf_templater import IDFTemplater
from resource_inventory.pdf_templater import PDFTemplater
from account.models import Downtime, UserProfile
from dashboard.utils import AbstractModelQuery


class JobStatus:
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

    def get_opsyss(self):
        return Opsys.objects.filter(from_lab=self.lab)

    def get_images(self):
        return Image.objects.filter(from_lab=self.lab)

    def get_image(self, image_id):
        return Image.objects.filter(from_lab=self.lab, lab_id=image_id)

    def get_opsys(self, opsys_id):
        return Opsys.objects.filter(from_lab=self.lab, lab_id=opsys_id)

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

    def get_analytics_job(self):
        """ Get analytics job with status new """
        jobs = Job.objects.filter(
            booking__lab=self.lab,
            job_type='DATA'
        )

        return self.serialize_jobs(jobs, status=JobStatus.NEW)

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


class GeneratedCloudConfig(models.Model):
    resource_id = models.CharField(max_length=200)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    rconfig = models.ForeignKey(ResourceConfiguration, on_delete=models.CASCADE)
    text = models.TextField(null=True, blank=True)

    def _normalize_username(self, username: str) -> str:
        # TODO: make usernames posix compliant
        return username

    def _get_ssh_string(self, username: str) -> str:
        user = User.objects.get(username=username)
        uprofile = user.userprofile

        ssh_file = uprofile.ssh_public_key

        escaped_file = ssh_file.open().read().decode(encoding="UTF-8").replace("\n", " ")

        return escaped_file

    def _serialize_users(self):
        """
        returns the dictionary to be placed behind the `users` field of the toplevel c-i dict
        """
        # conserves distro default user
        user_array = ["default"]

        users = list(self.booking.collaborators.all())
        users.append(self.booking.owner)
        for collaborator in users:
            userdict = {}

            # TODO: validate if usernames are valid as linux usernames (and provide an override potentially)
            userdict['name'] = self._normalize_username(collaborator.username)

            userdict['groups'] = "sudo"
            userdict['sudo'] = "ALL=(ALL) NOPASSWD:ALL"

            userdict['ssh_authorized_keys'] = [self._get_ssh_string(collaborator.username)]

            user_array.append(userdict)

        # user_array.append({
        #    "name": "opnfv",
        #    "passwd": "$6$k54L.vim1cLaEc4$5AyUIrufGlbtVBzuCWOlA1yV6QdD7Gr2MzwIs/WhuYR9ebSfh3Qlb7djkqzjwjxpnSAonK1YOabPP6NxUDccu.",
        #    "ssh_redirect_user": True,
        #    "sudo": "ALL=(ALL) NOPASSWD:ALL",
        #    "groups": "sudo",
        #    })

        return user_array

    # TODO: make this configurable
    def _serialize_sysinfo(self):
        defuser = {}
        defuser['name'] = 'opnfv'
        defuser['plain_text_passwd'] = 'OPNFV_HOST'
        defuser['home'] = '/home/opnfv'
        defuser['shell'] = '/bin/bash'
        defuser['lock_passwd'] = True
        defuser['gecos'] = 'Lab Manager User'
        defuser['groups'] = 'sudo'

        return {'default_user': defuser}

    # TODO: make this configurable
    def _serialize_runcmds(self):
        cmdlist = []

        # have hosts run dhcp on boot
        cmdlist.append(['sudo', 'dhclient', '-r'])
        cmdlist.append(['sudo', 'dhclient'])

        return cmdlist

    def _serialize_netconf_v1(self):
        # interfaces = {}  # map from iface_name => dhcp_config
        # vlans = {}  # map from vlan_id => dhcp_config

        config_arr = []

        for interface in self._resource().interfaces.all():
            interface_name = interface.profile.name
            interface_mac = interface.mac_address

            iface_dict_entry = {
                "type": "physical",
                "name": interface_name,
                "mac_address": interface_mac,
            }

            for vlan in interface.config.all():
                if vlan.tagged:
                    vlan_dict_entry = {'type': 'vlan'}
                    vlan_dict_entry['name'] = str(interface_name) + "." + str(vlan.vlan_id)
                    vlan_dict_entry['vlan_link'] = str(interface_name)
                    vlan_dict_entry['vlan_id'] = int(vlan.vlan_id)
                    vlan_dict_entry['mac_address'] = str(interface_mac)
                    if vlan.public:
                        vlan_dict_entry["subnets"] = [{"type": "dhcp"}]
                    config_arr.append(vlan_dict_entry)
                if (not vlan.tagged) and vlan.public:
                    iface_dict_entry["subnets"] = [{"type": "dhcp"}]

                # vlan_dict_entry['mtu'] = # TODO, determine override MTU if needed

            config_arr.append(iface_dict_entry)

        ns_dict = {
            'type': 'nameserver',
            'address': ['10.64.0.1', '8.8.8.8']
        }

        config_arr.append(ns_dict)

        full_dict = {'version': 1, 'config': config_arr}

        return full_dict

    @classmethod
    def get(cls, booking_id: int, resource_lab_id: str, file_id: int):
        return GeneratedCloudConfig.objects.get(resource_id=resource_lab_id, booking__id=booking_id, file_id=file_id)

    def _resource(self):
        return ResourceQuery.get(labid=self.resource_id, lab=self.booking.lab)

    # def _get_facts(self):
        # resource = self._resource()

        # hostname = self.rconfig.name
        # iface_configs = for_config.interface_configs.all()

    def _to_dict(self):
        main_dict = {}

        main_dict['users'] = self._serialize_users()
        main_dict['network'] = self._serialize_netconf_v1()
        main_dict['hostname'] = self.rconfig.name

        # add first startup commands
        main_dict['runcmd'] = self._serialize_runcmds()

        # configure distro default user
        main_dict['system_info'] = self._serialize_sysinfo()

        return main_dict

    def serialize(self) -> str:
        return yaml.dump(self._to_dict())


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
        sbook['resourceBundle'] = AutomationAPIManager.serialize_bundle(booking.resource)
        return sbook

    @staticmethod
    def serialize_lab(lab):
        slab = {}
        slab['id'] = lab.pk
        slab['name'] = lab.name
        return slab

    @staticmethod
    def serialize_bundle(bundle):
        sbundle = {}
        sbundle['id'] = bundle.pk
        sbundle['resources'] = [
            AutomationAPIManager.serialize_server(server)
            for server in bundle.get_resources()]
        return sbundle

    @staticmethod
    def serialize_server(server):
        sserver = {}
        sserver['id'] = server.pk
        sserver['name'] = server.name
        return sserver

    @staticmethod
    def serialize_resource_profile(profile):
        sprofile = {}
        sprofile['id'] = profile.pk
        sprofile['name'] = profile.name
        return sprofile

    @staticmethod
    def serialize_template(rec_temp_and_count):
        template = rec_temp_and_count[0]
        count = rec_temp_and_count[1]

        stemplate = {}
        stemplate['id'] = template.pk
        stemplate['name'] = template.name
        stemplate['count_available'] = count
        stemplate['resourceProfiles'] = [
            AutomationAPIManager.serialize_resource_profile(config.profile)
            for config in template.getConfigs()
        ]
        return stemplate

    @staticmethod
    def serialize_image(image):
        simage = {}
        simage['id'] = image.pk
        simage['name'] = image.name
        return simage

    @staticmethod
    def serialize_userprofile(up):
        sup = {}
        sup['id'] = up.pk
        sup['username'] = up.user.username
        return sup


class Job(models.Model):
    """
    A Job to be performed by the Lab.

    The API uses Jobs and Tasks to communicate actions that need to be taken to the Lab
    that is hosting a booking. A booking from a user has an associated Job which tells
    the lab how to configure the hardware, networking, etc to fulfill the booking
    for the user.
    This is the class that is serialized and put into the api
    """

    JOB_TYPES = (
        ('BOOK', 'Booking'),
        ('DATA', 'Analytics')
    )

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, null=True)
    status = models.IntegerField(default=JobStatus.NEW)
    complete = models.BooleanField(default=False)
    job_type = models.CharField(
        max_length=4,
        choices=JOB_TYPES,
        default='BOOK'
    )

    def to_dict(self):
        d = {}
        for relation in self.get_tasklist():
            if relation.job_key not in d:
                d[relation.job_key] = {}
            d[relation.job_key][relation.task_id] = relation.config.to_dict()

        return {"id": self.id, "payload": d}

    def get_tasklist(self, status="all"):
        if status != "all":
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
    state = models.IntegerField(default=ConfigState.NEW)

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
        hid = ResourceQuery.get(interface__pk=self.interfaces.first().pk).labid
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


class ActiveUsersConfig(models.Model):
    """
    Task for getting active VPN users

    StackStorm needs no information to run this job
    so this task is very bare, but neccessary to fit
    job creation convention.
    """

    def clear_delta(self):
        self.delta = '{}'

    def get_delta(self):
        return json.loads(self.to_json())

    def to_json(self):
        return json.dumps(self.to_dict())

    def to_dict(self):
        return {}


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
        return json.loads(self.to_json())


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
        d = json.loads(self.to_json())
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

    def to_dict(self):
        return self.get_delta()

    def get_delta(self):
        # TODO: grab the GeneratedCloudConfig urls from self.hosthardwarerelation.get_resource()
        return self.format_delta(
            self.hosthardwarerelation.get_resource().get_configuration(self.state),
            self.hosthardwarerelation.lab_token)


class NetworkConfig(TaskConfig):
    """Handles network configuration."""

    interfaces = models.ManyToManyField(Interface)
    delta = models.TextField()

    def to_dict(self):
        d = {}
        hid = self.hostnetworkrelation.resource_id
        d[hid] = {}
        for interface in self.interfaces.all():
            d[hid][interface.mac_address] = []
            if self.state != ConfigState.CLEAN:
                for vlan in interface.config.all():
                    # TODO: should this come from the interface?
                    # e.g. will different interfaces for different resources need different configs?
                    d[hid][interface.mac_address].append({"vlan_id": vlan.vlan_id, "tagged": vlan.tagged})

        return d

    def to_json(self):
        return json.dumps(self.to_dict())

    def get_delta(self):
        d = json.loads(self.to_json())
        d['lab_token'] = self.hostnetworkrelation.lab_token
        return d

    def clear_delta(self):
        self.delta = json.dumps(self.to_dict())
        self.save()

    def add_interface(self, interface):
        self.interfaces.add(interface)
        d = json.loads(self.delta)
        hid = self.hostnetworkrelation.resource_id
        if hid not in d:
            d[hid] = {}
        d[hid][interface.mac_address] = []
        for vlan in interface.config.all():
            d[hid][interface.mac_address].append({"vlan_id": vlan.vlan_id, "tagged": vlan.tagged})
        self.delta = json.dumps(d)


class SnapshotConfig(TaskConfig):

    resource_id = models.CharField(max_length=200, default="default_id")
    image = models.CharField(max_length=200, null=True)  # cobbler ID
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
        d = json.loads(self.to_json())
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

    def get_resource(self):
        return ResourceQuery.get(labid=self.resource_id)


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

    def get_resource(self):
        return ResourceQuery.get(labid=self.resource_id)


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


class ActiveUsersRelation(TaskRelation):
    config = models.OneToOneField(ActiveUsersConfig, on_delete=models.CASCADE)
    job_key = "active users task"

    def type_str(self):
        return "Active Users Task"


class JobFactory(object):
    """This class creates all the API models (jobs, tasks, etc) needed to fulfill a booking."""

    @classmethod
    def reimageHost(cls, new_image, booking, host):
        """Modify an existing job to reimage the given host."""
        job = Job.objects.get(booking=booking)
        # make hardware task new
        hardware_relation = HostHardwareRelation.objects.get(resource_id=host, job=job)
        hardware_relation.config.image = new_image.lab_id
        hardware_relation.config.save()
        hardware_relation.status = JobStatus.NEW

        # re-apply networking after host is reset
        net_relation = HostNetworkRelation.objects.get(resource_id=host, job=job)
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
    def makeActiveUsersTask(cls):
        """ Append active users task to analytics job """
        config = ActiveUsersConfig()
        relation = ActiveUsersRelation()
        job = Job.objects.get(job_type='DATA')

        job.status = JobStatus.NEW

        relation.job = job
        relation.config = config
        relation.config.save()
        relation.config = relation.config
        relation.save()
        config.save()

    @classmethod
    def makeAnalyticsJob(cls, booking):
        """
        Create the analytics job

        This will only run once since there will only be one analytics job.
        All analytics tasks get appended to analytics job.
        """

        if len(Job.objects.filter(job_type='DATA')) > 0:
            raise Exception("Cannot have more than one analytics job")

        if booking.resource:
            raise Exception("Booking is not marker for analytics job, has resoure")

        job = Job()
        job.booking = booking
        job.job_type = 'DATA'
        job.save()

        cls.makeActiveUsersTask()

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
        cls.makeGeneratedCloudConfigs(
            resources=resources,
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
    def makeGeneratedCloudConfigs(cls, resources=[], job=Job()):
        for res in resources:
            cif = GeneratedCloudConfig.objects.create(resource_id=res.labid, booking=job.booking, rconfig=res.config)
            cif.save()

            cif = CloudInitFile.create(priority=0, text=cif.serialize())
            cif.save()

            res.config.cloud_init_files.add(cif)
            res.config.save()

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
                hardware_config = HardwareConfig.objects.get(relation__resource_id=res.labid)
            except Exception:
                hardware_config = HardwareConfig()

            relation = HostHardwareRelation()
            relation.resource_id = res.labid
            relation.job = job
            relation.config = hardware_config
            relation.config.save()
            relation.config = relation.config
            relation.save()

            hardware_config.set("id", "image", "hostname", "power", "ipmi_create")
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
        if len(booking.resource.get_resources()) < 2:
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

        for host in booking.resource.get_resources():
            opnfv_api_config.roles.add(host)
        software_config = SoftwareConfig.objects.create(opnfv=opnfv_api_config)
        software_relation = SoftwareRelation.objects.create(job=job, config=software_config)
        return software_relation


JOB_TASK_CLASSLIST = [
    HostHardwareRelation,
    AccessRelation,
    HostNetworkRelation,
    SoftwareRelation,
    SnapshotRelation,
    ActiveUsersRelation
]


class JobTaskQuery(AbstractModelQuery):
    model_list = JOB_TASK_CLASSLIST
