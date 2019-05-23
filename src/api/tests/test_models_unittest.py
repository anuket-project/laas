##############################################################################
# Copyright (c) 2019 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from api.models import (
    Job,
    JobStatus,
    JobFactory,
    HostNetworkRelation,
    HostHardwareRelation,
    SoftwareRelation,
    AccessConfig,
)

from resource_inventory.models import (
    OPNFVRole,
    HostProfile,
)

from django.test import TestCase, Client

from dashboard.testing_utils import (
    make_host,
    make_user,
    make_user_profile,
    make_lab,
    make_installer,
    make_image,
    make_scenario,
    make_os,
    make_complete_host_profile,
    make_booking,
)


class ValidBookingCreatesValidJob(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user(False, username="newtestuser", password="testpassword")
        cls.userprofile = make_user_profile(cls.user)
        cls.lab = make_lab()

        cls.host_profile = make_complete_host_profile(cls.lab)
        cls.scenario = make_scenario()
        cls.installer = make_installer([cls.scenario])
        os = make_os([cls.installer])
        cls.image = make_image(cls.lab, 1, cls.user, os, cls.host_profile)
        for i in range(30):
            make_host(cls.host_profile, cls.lab, name="host" + str(i), labid="host" + str(i))
        cls.client = Client()

    def setUp(self):
        self.booking, self.compute_hostnames, self.jump_hostname = self.create_multinode_generic_booking()

    def create_multinode_generic_booking(self):
        topology = {}

        compute_hostnames = ["cmp01", "cmp02", "cmp03"]

        host_type = HostProfile.objects.first()

        universal_networks = [
            {"name": "public", "tagged": False, "public": True},
            {"name": "admin", "tagged": True, "public": False}]
        compute_networks = [{"name": "private", "tagged": True, "public": False}]
        jumphost_networks = [{"name": "external", "tagged": True, "public": True}]

        # generate a bunch of extra networks
        for i in range(10):
            net = {"tagged": False, "public": False}
            net["name"] = "net" + str(i)
            universal_networks.append(net)

        jumphost_info = {
            "type": host_type,
            "role": OPNFVRole.objects.get_or_create(name="Jumphost")[0],
            "nets": self.make_networks(host_type, jumphost_networks + universal_networks),
            "image": self.image
        }
        topology["jump"] = jumphost_info

        for hostname in compute_hostnames:
            host_info = {
                "type": host_type,
                "role": OPNFVRole.objects.get_or_create(name="Compute")[0],
                "nets": self.make_networks(host_type, compute_networks + universal_networks),
                "image": self.image
            }
            topology[hostname] = host_info

        booking = make_booking(
            owner=self.user,
            lab=self.lab,
            topology=topology,
            installer=self.installer,
            scenario=self.scenario
        )

        if not booking.resource:
            raise Exception("Booking does not have a resource when trying to pass to makeCompleteJob")
        JobFactory.makeCompleteJob(booking)

        return booking, compute_hostnames, "jump"

    def make_networks(self, hostprofile, nets):
        """
        distributes nets accross hostprofile's interfaces
        returns a 2D array
        """
        network_struct = []
        count = hostprofile.interfaceprofile.all().count()
        for i in range(count):
            network_struct.append([])
        while(nets):
            index = len(nets) % count
            network_struct[index].append(nets.pop())

        return network_struct

    # begin tests

    def test_valid_access_configs(self):
        job = Job.objects.get(booking=self.booking)
        self.assertIsNotNone(job)

        access_configs = AccessConfig.objects.filter(accessrelation__job=job)

        vpn_configs = access_configs.filter(access_type="vpn")
        ssh_configs = access_configs.filter(access_type="ssh")

        self.assertFalse(AccessConfig.objects.exclude(access_type__in=["vpn", "ssh"]).exists())

        all_users = list(self.booking.collaborators.all())
        all_users.append(self.booking.owner)

        for user in all_users:
            self.assertTrue(vpn_configs.filter(user=user).exists())
            self.assertTrue(ssh_configs.filter(user=user).exists())

    def test_valid_network_configs(self):
        job = Job.objects.get(booking=self.booking)
        self.assertIsNotNone(job)

        booking_hosts = self.booking.resource.hosts.all()

        netrelations = HostNetworkRelation.objects.filter(job=job)
        netconfigs = [r.config for r in netrelations]

        netrelation_hosts = [r.host for r in netrelations]

        for config in netconfigs:
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

        hardware_relations = HostHardwareRelation.objects.filter(job=job)

        job_hosts = [r.host for r in hardware_relations]

        booking_hosts = self.booking.resource.hosts.all()

        self.assertEqual(len(booking_hosts), len(job_hosts))

        for relation in hardware_relations:
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
