##############################################################################
# Copyright (c) 2019 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from datetime import timedelta
from django.utils import timezone

from booking.models import Booking
from api.models import (
    Job,
    JobStatus,
    JobFactory,
    AccessRelation,
    HostNetworkRelation,
    HostHardwareRelation,
    SoftwareRelation,
)

from resource_inventory.models import (
    OPNFVRole,
    HostProfile,
)

from django.test import TestCase, Client

from dashboard.testing_utils import (
    instantiate_host,
    instantiate_user,
    instantiate_userprofile,
    instantiate_lab,
    instantiate_installer,
    instantiate_image,
    instantiate_scenario,
    instantiate_os,
    make_hostprofile_set,
    instantiate_opnfvrole,
    instantiate_publicnet,
    instantiate_booking,
)


class ValidBookingCreatesValidJob(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.loginuser = instantiate_user(False, username="newtestuser", password="testpassword")
        cls.userprofile = instantiate_userprofile(cls.loginuser)

        lab_user = instantiate_user(True)
        cls.lab = instantiate_lab(lab_user)

        cls.host_profile = make_hostprofile_set(cls.lab)
        cls.scenario = instantiate_scenario()
        cls.installer = instantiate_installer([cls.scenario])
        os = instantiate_os([cls.installer])
        cls.image = instantiate_image(cls.lab, 1, cls.loginuser, os, cls.host_profile)
        for i in range(30):
            instantiate_host(cls.host_profile, cls.lab, name="host" + str(i), labid="host" + str(i))
        cls.role = instantiate_opnfvrole("Jumphost")
        cls.computerole = instantiate_opnfvrole("Compute")
        instantiate_publicnet(10, cls.lab)
        instantiate_publicnet(12, cls.lab)
        instantiate_publicnet(14, cls.lab)

        cls.lab_selected = 'lab_' + str(cls.lab.lab_user.id) + '_selected'
        cls.host_selected = 'host_' + str(cls.host_profile.id) + '_selected'

        cls.post_data = cls.build_post_data()

        cls.client = Client()

    def setUp(self):
        self.client.login(
            username=self.loginuser.username, password="testpassword")
        self.booking, self.compute_hostnames, self.jump_hostname = self.create_multinode_generic_booking()

    @classmethod
    def build_post_data(cls):
        post_data = {}
        post_data['filter_field'] = '{"hosts":[{"host_' + str(cls.host_profile.id) + '":"true"}], "labs": [{"lab_' + str(cls.lab.lab_user.id) + '":"true"}]}'
        post_data['purpose'] = 'purposefieldcontentstring'
        post_data['project'] = 'projectfieldcontentstring'
        post_data['length'] = '3'
        post_data['ignore_this'] = 1
        post_data['users'] = ''
        post_data['hostname'] = 'hostnamefieldcontentstring'
        post_data['image'] = str(cls.image.id)
        post_data['installer'] = str(cls.installer.id)
        post_data['scenario'] = str(cls.scenario.id)
        return post_data

    def post(self, changed_fields={}):
        payload = self.post_data.copy()
        payload.update(changed_fields)
        response = self.client.post('/booking/quick/', payload)
        return response

    def generate_booking(self):
        self.post()
        return Booking.objects.first()

    def test_valid_access_configs(self):
        job = Job.objects.get(booking=self.booking)
        self.assertIsNotNone(job)

        access_configs = [r.config for r in AccessRelation.objects.filter(job=job).all()]

        vpnconfigs = []
        sshconfigs = []

        for config in access_configs:
            if config.access_type == "vpn":
                vpnconfigs.append(config)
            elif config.access_type == "ssh":
                sshconfigs.append(config)
            else:
                self.fail(msg="Undefined accessconfig: " + config.access_type + " found")

        user_set = []
        user_set.append(self.booking.owner)
        user_set += self.booking.collaborators.all()

        for configs in [vpnconfigs, sshconfigs]:
            for user in user_set:
                configusers = [c.user for c in configs]
                self.assertTrue(user in configusers)

    def test_valid_network_configs(self):
        job = Job.objects.get(booking=self.booking)
        self.assertIsNotNone(job)

        booking_hosts = self.booking.resource.hosts.all()

        netrelation_set = HostNetworkRelation.objects.filter(job=job)
        netconfig_set = [r.config for r in netrelation_set]

        netrelation_hosts = [r.host for r in netrelation_set]

        for config in netconfig_set:
            for interface in config.interfaces.all():
                self.assertTrue(interface.host in booking_hosts)

        # if no interfaces are referenced that shouldn't have vlans,
        # and no vlans exist outside those accounted for in netconfigs,
        # then the api is faithfully representing networks
        # as netconfigs reference resource_inventory models directly

        # this test relies on the assumption that
        # every interface is configured, whether it does or does not have vlans
        # if this is not true, the  test fails

        for host in booking_hosts:
            self.assertTrue(host in netrelation_hosts)
            relation = HostNetworkRelation.objects.filter(job=job).get(host=host)

            # do 2 direction matching that interfaces are one to one
            config = relation.config
            for interface in config.interfaces.all():
                self.assertTrue(interface in host.interfaces)
            for interface in host.interfaces.all():
                self.assertTrue(interface in config.interfaces)

        for host in netrelation_hosts:
            self.assertTrue(host in booking_hosts)

    def test_valid_hardware_configs(self):
        job = Job.objects.get(booking=self.booking)
        self.assertIsNotNone(job)

        hrelations = HostHardwareRelation.objects.filter(job=job).all()

        job_hosts = [r.host for r in hrelations]

        booking_hosts = self.booking.resource.hosts.all()

        self.assertEqual(len(booking_hosts), len(job_hosts))

        for relation in hrelations:
            self.assertTrue(relation.host in booking_hosts)
            self.assertEqual(relation.status, JobStatus.NEW)
            config = relation.config
            host = relation.host
            self.assertEqual(config.hostname, host.template.resource.name)

    def test_valid_software_configs(self):
        job = Job.objects.get(booking=self.booking)
        self.assertIsNotNone(job)

        srelation = SoftwareRelation.objects.filter(job=job).first()
        self.assertIsNotNone(srelation)

        sconfig = srelation.config
        self.assertIsNotNone(sconfig)

        oconfig = sconfig.opnfv
        self.assertIsNotNone(oconfig)

        # not onetoone in models, but first() is safe here based on how ConfigBundle and a matching OPNFVConfig are created
        # this should, however, be made explicit
        self.assertEqual(oconfig.installer, self.booking.config_bundle.opnfv_config.first().installer.name)
        self.assertEqual(oconfig.scenario, self.booking.config_bundle.opnfv_config.first().scenario.name)

        for host in oconfig.roles.all():
            role_name = host.config.opnfvRole.name
            if str(role_name) == "Jumphost":
                self.assertEqual(host.template.resource.name, self.jump_hostname)
            elif str(role_name) == "Compute":
                self.assertTrue(host.template.resource.name in self.compute_hostnames)
            else:
                self.fail(msg="Host with non-configured role name related to job: " + str(role_name))

    def create_multinode_generic_booking(self):
        topology = {}

        compute_hostnames = ["cmp01", "cmp02", "cmp03"]

        host_type = HostProfile.objects.first()

        universal_networks = [
            {"name": "public", "tagged": False, "public": True},
            {"name": "admin", "tagged": True, "public": False}]
        just_compute_networks = [{"name": "private", "tagged": True, "public": False}]
        just_jumphost_networks = [{"name": "external", "tagged": True, "public": True}]

        # generate a bunch of extra networks
        for i in range(10):
            net = {"tagged": False, "public": False}
            net["name"] = "u_net" + str(i)
            universal_networks.append(net)

        jhost_info = {}
        jhost_info["type"] = host_type
        jhost_info["role"] = OPNFVRole.objects.get(name="Jumphost")
        jhost_info["nets"] = self.make_networks(host_type, list(just_jumphost_networks + universal_networks))
        jhost_info["image"] = self.image
        topology["jump"] = jhost_info

        for hostname in compute_hostnames:
            host_info = {}
            host_info["type"] = host_type
            host_info["role"] = OPNFVRole.objects.get(name="Compute")
            host_info["nets"] = self.make_networks(host_type, list(just_compute_networks + universal_networks))
            host_info["image"] = self.image
            topology[hostname] = host_info

        booking = instantiate_booking(self.loginuser,
                                      timezone.now(),
                                      timezone.now() + timedelta(days=1),
                                      "demobooking",
                                      self.lab,
                                      topology=topology,
                                      installer=self.installer,
                                      scenario=self.scenario)

        if not booking.resource:
            raise Exception("Booking does not have a resource when trying to pass to makeCompleteJob")
        JobFactory.makeCompleteJob(booking)

        return booking, compute_hostnames, "jump"

    """
    evenly distributes networks given across a given profile's interfaces
    """
    def make_networks(self, hostprofile, nets):
        network_struct = []
        count = hostprofile.interfaceprofile.all().count()
        for i in range(count):
            network_struct.append([])
        while(nets):
            index = len(nets) % count
            network_struct[index].append(nets.pop())

        return network_struct
