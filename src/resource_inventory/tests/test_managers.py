##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.test import TestCase
from django.contrib.auth.models import User

from resource.inventory_manager import InventoryManager
from resource.resource_manager import ResourceManager
from resource.models import *


class InventoryManagerTestCase(TestCase):

    def test_singleton(self):
        instance = InventoryManager.getInstance()
        self.assertTrue(isinstance(instance, InventoryManager))
        self.assertTrue(instance is InventoryManager.getInstance())

    def setUp(self):
        # setup
        # create lab and give it resources
        user = User.objects.create(username="username")
        self.lab = Lab.objects.create(
            lab_user=user,
            name='test lab',
            contact_email='someone@email.com',
            contact_phone='dont call me'
        )

        # create hostProfile
        hostProfile = HostProfile.objects.create(
            host_type=0,
            name='Test profile',
            description='a test profile'
        )
        interfaceProfile = InterfaceProfile.objects.create(
            speed=1000,
            name='eno3',
            host=hostProfile
        )
        diskProfile = DiskProfile.objects.create(
            size=1000,
            media_type="SSD",
            name='/dev/sda',
            host=hostProfile
        )
        cpuProfile = CpuProfile.objects.create(
            cores=96,
            architecture="x86_64",
            cpus=2,
            host=hostProfile
        )
        ramProfile = RamProfile.objects.create(
            amount=256,
            channels=4,
            host=hostProfile
        )

        #create GenericResourceBundle
        genericBundle = GenericResourceBundle.objects.create()

        self.gHost1 = GenericHost.objects.create(
            bundle=genericBundle,
            name='generic host 1',
            profile=hostProfile
        )
        self.gHost2 = GenericHost.objects.create(
            bundle=genericBundle,
            name='generic host 2',
            profile=hostProfile
        )

        #actual resource bundle
        bundle = ResourceBundle.objects.create(template=genericBundle)

        self.host1 = Host.objects.create(
            template=self.gHost1,
            booked=True,
            name='host1',
            bundle=bundle,
            profile=hostProfile,
            lab=self.lab
        )

        self.host2 = Host.objects.create(
            template=self.gHost2,
            booked=True,
            name='host2',
            bundle=bundle,
            profile=hostProfile,
            lab=self.lab
        )

        vlan1 = Vlan.objects.create(vlan_id=300, tagged=False)
        vlan2 = Vlan.objects.create(vlan_id=300, tagged=False)

        iface1 = Interface.objects.create(
            mac_address='00:11:22:33:44:55',
            bus_address='some bus address',
            switch_name='switch1',
            port_name='port10',
            config=vlan1,
            host=self.host1
        )
        iface2 = Interface.objects.create(
            mac_address='00:11:22:33:44:56',
            bus_address='some bus address',
            switch_name='switch1',
            port_name='port12',
            config=vlan2,
            host=self.host2
        )

    def test_acquire_host(self):
        host = InventoryManager.getInstance().acquireHost(self.gHost1, self.lab.name)
        self.assertNotEquals(host, None)
        self.assertTrue(host.booked)
        self.assertEqual(host.template, self.gHost1)

    def test_release_host(self):
        host = InventoryManager.getInstance().acquireHost(self.gHost1, self.lab.name)
        self.assertTrue(host.booked)
        InventoryManager.getInstance().releaseHost(host)
        self.assertFalse(host.booked)


class ResourceManagerTestCase(TestCase):
    def test_singleton(self):
        instance = ResourceManager.getInstance()
        self.assertTrue(isinstance(instance, ResourceManager))
        self.assertTrue(instance is ResourceManager.getInstance())

    def setUp(self):
        # setup
        # create lab and give it resources
        user = User.objects.create(username="username")
        self.lab = Lab.objects.create(
            lab_user=user,
            name='test lab',
            contact_email='someone@email.com',
            contact_phone='dont call me'
        )

        # create hostProfile
        hostProfile = HostProfile.objects.create(
            host_type=0,
            name='Test profile',
            description='a test profile'
        )
        interfaceProfile = InterfaceProfile.objects.create(
            speed=1000,
            name='eno3',
            host=hostProfile
        )
        diskProfile = DiskProfile.objects.create(
            size=1000,
            media_type="SSD",
            name='/dev/sda',
            host=hostProfile
        )
        cpuProfile = CpuProfile.objects.create(
            cores=96,
            architecture="x86_64",
            cpus=2,
            host=hostProfile
        )
        ramProfile = RamProfile.objects.create(
            amount=256,
            channels=4,
            host=hostProfile
        )

        #create GenericResourceBundle
        genericBundle = GenericResourceBundle.objects.create()

        self.gHost1 = GenericHost.objects.create(
            bundle=genericBundle,
            name='generic host 1',
            profile=hostProfile
        )
        self.gHost2 = GenericHost.objects.create(
            bundle=genericBundle,
            name='generic host 2',
            profile=hostProfile
        )

        #actual resource bundle
        bundle = ResourceBundle.objects.create(template=genericBundle)

        self.host1 = Host.objects.create(
            template=self.gHost1,
            booked=True,
            name='host1',
            bundle=bundle,
            profile=hostProfile,
            lab=self.lab
        )

        self.host2 = Host.objects.create(
            template=self.gHost2,
            booked=True,
            name='host2',
            bundle=bundle,
            profile=hostProfile,
            lab=self.lab
        )

        vlan1 = Vlan.objects.create(vlan_id=300, tagged=False)
        vlan2 = Vlan.objects.create(vlan_id=300, tagged=False)

        iface1 = Interface.objects.create(
            mac_address='00:11:22:33:44:55',
            bus_address='some bus address',
            switch_name='switch1',
            port_name='port10',
            config=vlan1,
            host=self.host1
        )
        iface2 = Interface.objects.create(
            mac_address='00:11:22:33:44:56',
            bus_address='some bus address',
            switch_name='switch1',
            port_name='port12',
            config=vlan2,
            host=self.host2
        )

    def test_convert_bundle(self):
        bundle = ResourceManager.getInstance().convertResoureBundle(self.genericBundle, self.lab.name)
        # verify bundle configuration
