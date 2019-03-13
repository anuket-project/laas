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
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

import json
import uuid

from booking.models import Booking
from resource_inventory.models import (
    Lab,
    HostProfile,
    Host,
    Image,
    Interface,
    RemoteInfo
)


class JobStatus(object):
    NEW = 0
    CURRENT = 100
    DONE = 200
    ERROR = 300


class LabManagerTracker(object):

    @classmethod
    def get(cls, lab_name, token):
        """
        Takes in a lab name (from a url path)
        returns a lab manager instance for that lab, if it exists
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
    This is the class that will ultimately handle all REST calls to
    lab endpoints.
    handles jobs, inventory, status, etc
    may need to create helper classes
    """

    def __init__(self, lab):
        self.lab = lab

    def update_host_remote_info(self, data, host_id):
        host = get_object_or_404(Host, labid=host_id, lab=self.lab)
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
        remote_info = host.remote_management
        if "default" in remote_info.mac_address:
            remote_info = RemoteInfo()
        remote_info.address = info['address']
        remote_info.mac_address = info['mac_address']
        remote_info.password = info['password']
        remote_info.user = info['user']
        remote_info.type = info['type']
        remote_info.versions = info['versions']
        remote_info.save()
        host.remote_management = remote_info
        host.save()
        return {"status": "success"}

    def get_profile(self):
        prof = {}
        prof['name'] = self.lab.name
        prof['contact'] = {
            "phone": self.lab.contact_phone,
            "email": self.lab.contact_email
        }
        prof['host_count'] = []
        for host in HostProfile.objects.filter(labs=self.lab):
            count = Host.objects.filter(profile=host, lab=self.lab).count()
            prof['host_count'].append(
                {
                    "type": host.name,
                    "count": count
                }
            )
        return prof

    def get_inventory(self):
        inventory = {}
        hosts = Host.objects.filter(lab=self.lab)
        images = Image.objects.filter(from_lab=self.lab)
        profiles = HostProfile.objects.filter(labs=self.lab)
        inventory['hosts'] = self.serialize_hosts(hosts)
        inventory['images'] = self.serialize_images(images)
        inventory['host_types'] = self.serialize_host_profiles(profiles)
        return inventory

    def get_host(self, hostname):
        host = get_object_or_404(Host, labid=hostname, lab=self.lab)
        return {
            "booked": host.booked,
            "working": host.working,
            "type": host.profile.name
        }

    def update_host(self, hostname, data):
        host = get_object_or_404(Host, labid=hostname, lab=self.lab)
        if "working" in data:
            working = data['working'] == "true"
            host.working = working
        host.save()
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

    def serialize_hosts(self, hosts):
        host_ser = []
        for host in hosts:
            h = {}
            h['interfaces'] = []
            h['hostname'] = host.name
            h['host_type'] = host.profile.name
            for iface in host.interfaces.all():
                eth = {}
                eth['mac'] = iface.mac_address
                eth['busaddr'] = iface.bus_address
                eth['name'] = iface.name
                eth['switchport'] = {"switch_name": iface.switch_name, "port_name": iface.port_name}
                h['interfaces'].append(eth)
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

    def serialize_host_profiles(self, profiles):
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
    This is the class that is serialized and put into the api
    """
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, null=True)
    status = models.IntegerField(default=JobStatus.NEW)
    complete = models.BooleanField(default=False)

    def to_dict(self):
        d = {}
        j = {}
        j['id'] = self.id
        for relation in AccessRelation.objects.filter(job=self):
            if 'access' not in d:
                d['access'] = {}
            d['access'][relation.task_id] = relation.config.to_dict()
        for relation in SoftwareRelation.objects.filter(job=self):
            if 'software' not in d:
                d['software'] = {}
            d['software'][relation.task_id] = relation.config.to_dict()
        for relation in HostHardwareRelation.objects.filter(job=self):
            if 'hardware' not in d:
                d['hardware'] = {}
            d['hardware'][relation.task_id] = relation.config.to_dict()
        for relation in HostNetworkRelation.objects.filter(job=self):
            if 'network' not in d:
                d['network'] = {}
            d['network'][relation.task_id] = relation.config.to_dict()
        for relation in SnapshotRelation.objects.filter(job=self):
            if 'snapshot' not in d:
                d['snapshot'] = {}
            d['snapshot'][relation.task_id] = relation.config.to_dict()

        j['payload'] = d

        return j

    def get_tasklist(self, status="all"):
        tasklist = []
        clist = [
            HostHardwareRelation,
            AccessRelation,
            HostNetworkRelation,
            SoftwareRelation,
            SnapshotRelation
        ]
        if status == "all":
            for cls in clist:
                tasklist += list(cls.objects.filter(job=self))
        else:
            for cls in clist:
                tasklist += list(cls.objects.filter(job=self).filter(status=status))
        return tasklist

    def is_fulfilled(self):
        """
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
        j = {}
        j['id'] = self.id
        for relation in AccessRelation.objects.filter(job=self).filter(status=status):
            if 'access' not in d:
                d['access'] = {}
            d['access'][relation.task_id] = relation.config.get_delta()
        for relation in SoftwareRelation.objects.filter(job=self).filter(status=status):
            if 'software' not in d:
                d['software'] = {}
            d['software'][relation.task_id] = relation.config.get_delta()
        for relation in HostHardwareRelation.objects.filter(job=self).filter(status=status):
            if 'hardware' not in d:
                d['hardware'] = {}
            d['hardware'][relation.task_id] = relation.config.get_delta()
        for relation in HostNetworkRelation.objects.filter(job=self).filter(status=status):
            if 'network' not in d:
                d['network'] = {}
            d['network'][relation.task_id] = relation.config.get_delta()
        for relation in SnapshotRelation.objects.filter(job=self).filter(status=status):
            if 'snapshot' not in d:
                d['snapshot'] = {}
            d['snapshot'][relation.task_id] = relation.config.get_delta()

        j['payload'] = d
        return j

    def to_json(self):
        return json.dumps(self.to_dict())


class TaskConfig(models.Model):
    def to_dict(self):
        pass

    def get_delta(self):
        pass

    def to_json(self):
        return json.dumps(self.to_dict())

    def clear_delta(self):
        self.delta = '{}'


class OpnfvApiConfig(models.Model):

    installer = models.CharField(max_length=200)
    scenario = models.CharField(max_length=300)
    roles = models.ManyToManyField(Host)
    delta = models.TextField()

    def to_dict(self):
        d = {}
        if self.installer:
            d['installer'] = self.installer
        if self.scenario:
            d['scenario'] = self.scenario

        hosts = self.roles.all()
        if hosts.exists():
            d['roles'] = []
        for host in self.roles.all():
            d['roles'].append({host.labid: host.config.opnfvRole.name})

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
    """
    handled opnfv installations, etc
    """
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
    """
    handles imaging, user accounts, etc
    """
    image = models.CharField(max_length=100, default="defimage")
    power = models.CharField(max_length=100, default="off")
    hostname = models.CharField(max_length=100, default="hostname")
    ipmi_create = models.BooleanField(default=False)
    delta = models.TextField()

    def to_dict(self):
        d = {}
        d['image'] = self.image
        d['power'] = self.power
        d['hostname'] = self.hostname
        d['ipmi_create'] = str(self.ipmi_create)
        d['id'] = self.hosthardwarerelation.host.labid
        return d

    def to_json(self):
        return json.dumps(self.to_dict())

    def get_delta(self):
        if not self.delta:
            self.delta = self.to_json()
            self.save()
        d = json.loads(self.delta)
        d['lab_token'] = self.hosthardwarerelation.lab_token
        return d

    def clear_delta(self):
        d = {}
        d["id"] = self.hosthardwarerelation.host.labid
        d["lab_token"] = self.hosthardwarerelation.lab_token
        self.delta = json.dumps(d)

    def set_image(self, image):
        self.image = image
        d = json.loads(self.delta)
        d['image'] = self.image
        self.delta = json.dumps(d)

    def set_power(self, power):
        self.power = power
        d = json.loads(self.delta)
        d['power'] = power
        self.delta = json.dumps(d)

    def set_hostname(self, hostname):
        self.hostname = hostname
        d = json.loads(self.delta)
        d['hostname'] = hostname
        self.delta = json.dumps(d)

    def set_ipmi_create(self, ipmi_create):
        self.ipmi_create = ipmi_create
        d = json.loads(self.delta)
        d['ipmi_create'] = ipmi_create
        self.delta = json.dumps(d)


class NetworkConfig(TaskConfig):
    """
    handles network configuration
    """
    interfaces = models.ManyToManyField(Interface)
    delta = models.TextField()

    def to_dict(self):
        d = {}
        hid = self.hostnetworkrelation.host.labid
        d[hid] = {}
        for interface in self.interfaces.all():
            d[hid][interface.mac_address] = []
            for vlan in interface.config.all():
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

    host = models.ForeignKey(Host, null=True, on_delete=models.DO_NOTHING)
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
    status = models.IntegerField(default=JobStatus.NEW)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    config = models.OneToOneField(TaskConfig, on_delete=models.CASCADE)
    task_id = models.CharField(default=get_task_uuid, max_length=37)
    lab_token = models.CharField(default="null", max_length=50)
    message = models.TextField(default="")

    def delete(self, *args, **kwargs):
        self.config.delete()
        return super(self.__class__, self).delete(*args, **kwargs)

    def type_str(self):
        return "Generic Task"

    class Meta:
        abstract = True


class AccessRelation(TaskRelation):
    config = models.OneToOneField(AccessConfig, on_delete=models.CASCADE)

    def type_str(self):
        return "Access Task"

    def delete(self, *args, **kwargs):
        self.config.delete()
        return super(self.__class__, self).delete(*args, **kwargs)


class SoftwareRelation(TaskRelation):
    config = models.OneToOneField(SoftwareConfig, on_delete=models.CASCADE)

    def type_str(self):
        return "Software Configuration Task"

    def delete(self, *args, **kwargs):
        self.config.delete()
        return super(self.__class__, self).delete(*args, **kwargs)


class HostHardwareRelation(TaskRelation):
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    config = models.OneToOneField(HardwareConfig, on_delete=models.CASCADE)

    def type_str(self):
        return "Hardware Configuration Task"

    def get_delta(self):
        return self.config.to_dict()

    def delete(self, *args, **kwargs):
        self.config.delete()
        return super(self.__class__, self).delete(*args, **kwargs)


class HostNetworkRelation(TaskRelation):
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    config = models.OneToOneField(NetworkConfig, on_delete=models.CASCADE)

    def type_str(self):
        return "Network Configuration Task"

    def delete(self, *args, **kwargs):
        self.config.delete()
        return super(self.__class__, self).delete(*args, **kwargs)


class SnapshotRelation(TaskRelation):
    snapshot = models.ForeignKey(Image, on_delete=models.CASCADE)
    config = models.OneToOneField(SnapshotConfig, on_delete=models.CASCADE)

    def type_str(self):
        return "Snapshot Task"

    def get_delta(self):
        return self.config.to_dict()

    def delete(self, *args, **kwargs):
        self.config.delete()
        return super(self.__class__, self).delete(*args, **kwargs)


class JobFactory(object):

    @classmethod
    def reimageHost(cls, new_image, booking, host):
        """
        This method will make all necessary changes to make a lab
        reimage a host.
        """
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
        ssh_relation = AccessRelation.objects.get(job=job, config__access_type="ssh")
        ssh_relation.status = JobStatus.NEW

        # save them all at once to reduce the chance
        # of a lab polling and only seeing partial change
        hardware_relation.save()
        net_relation.save()
        ssh_relation.save()

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
        hosts = Host.objects.filter(bundle=booking.resource)
        job = None
        try:
            job = Job.objects.get(booking=booking)
        except Exception:
            job = Job.objects.create(status=JobStatus.NEW, booking=booking)
        cls.makeHardwareConfigs(
            hosts=hosts,
            job=job
        )
        cls.makeNetworkConfigs(
            hosts=hosts,
            job=job
        )
        cls.makeSoftware(
            hosts=hosts,
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
                        "hosts": [host.labid for host in hosts]
                    }
                )
            except Exception:
                continue

    @classmethod
    def makeHardwareConfigs(cls, hosts=[], job=Job()):
        for host in hosts:
            hardware_config = None
            try:
                hardware_config = HardwareConfig.objects.get(relation__host=host)
            except Exception:
                hardware_config = HardwareConfig()

            relation = HostHardwareRelation()
            relation.host = host
            relation.job = job
            relation.config = hardware_config
            relation.config.save()
            relation.config = relation.config
            relation.save()

            hardware_config.clear_delta()
            hardware_config.set_image(host.config.image.lab_id)
            hardware_config.set_hostname(host.template.resource.name)
            hardware_config.set_power("on")
            hardware_config.set_ipmi_create(True)
            hardware_config.save()

    @classmethod
    def makeAccessConfig(cls, users, access_type, revoke=False, job=Job(), context=False):
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
    def makeNetworkConfigs(cls, hosts=[], job=Job()):
        for host in hosts:
            network_config = None
            try:
                network_config = NetworkConfig.objects.get(relation__host=host)
            except Exception:
                network_config = NetworkConfig.objects.create()

            relation = HostNetworkRelation()
            relation.host = host
            relation.job = job
            network_config.save()
            relation.config = network_config
            relation.save()
            network_config.clear_delta()

            for interface in host.interfaces.all():
                network_config.add_interface(interface)
            network_config.save()

    @classmethod
    def makeSoftware(cls, hosts=[], job=Job()):
        def init_config(host):
            opnfv_config = OpnfvApiConfig()
            if host is not None:
                opnfv = host.config.bundle.opnfv_config.first()
                opnfv_config.installer = opnfv.installer.name
                opnfv_config.scenario = opnfv.scenario.name
            opnfv_config.save()
            return opnfv_config

        try:
            host = None
            if len(hosts) > 0:
                host = hosts[0]
            opnfv_config = init_config(host)

            for host in hosts:
                opnfv_config.roles.add(host)
            software_config = SoftwareConfig.objects.create(opnfv=opnfv_config)
            software_config.save()
            software_relation = SoftwareRelation.objects.create(job=job, config=software_config)
            software_relation.save()
            return software_relation
        except Exception:
            return None
