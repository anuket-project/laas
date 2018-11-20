##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
from django.test import TestCase
from booking.models import Booking
from account.models import Lab
from api.serializers.booking_serializer import BookingField
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import Permission, User
from resource_inventory.models import (
    Image,
    OPNFVRole,
    HostConfiguration,
    HostProfile,
    InterfaceProfile,
    DiskProfile,
    CpuProfile,
    RamProfile,
    GenericResourceBundle,
    GenericResource,
    GenericHost,
    Host,
    Vlan,
    Interface,
    ConfigBundle,
    ResourceBundle
)


class BookingSerializerTestCase(TestCase):

    count = 0

    def makeHostConfigurations(self, hosts, config):
        lab_user = User.objects.create(username="asfasdfasdf")
        owner = User.objects.create(username="asfasdfasdffffff")
        lab = Lab.objects.create(
            lab_user=lab_user,
            name="TestLab123123",
            contact_email="mail@email.com",
            contact_phone=""
        )
        jumphost = True
        for host in hosts:
            image = Image.objects.create(
                lab_id=12,
                from_lab=lab,
                name="this is a test image",
                owner=owner
            )
            name = "jumphost"
            if not jumphost:
                name = "compute"
            role = OPNFVRole.objects.create(
                name=name,
                description="stuff"
            )

            HostConfiguration.objects.create(
                host=host,
                image=image,
                bundle=config,
                opnfvRole=role
            )
            jumphost = False

    def setUp(self):
        self.serializer = BookingField()
        lab_user = User.objects.create(username="lab user")
        lab = Lab.objects.create(name="test lab", lab_user=lab_user)
        # create hostProfile
        hostProfile = HostProfile.objects.create(
            host_type=0,
            name='Test profile',
            description='a test profile'
        )
        InterfaceProfile.objects.create(
            speed=1000,
            name='eno3',
            host=hostProfile
        )
        DiskProfile.objects.create(
            size=1000,
            media_type="SSD",
            name='/dev/sda',
            host=hostProfile
        )
        CpuProfile.objects.create(
            cores=96,
            architecture="x86_64",
            cpus=2,
            host=hostProfile
        )
        RamProfile.objects.create(
            amount=256,
            channels=4,
            host=hostProfile
        )

        # create GenericResourceBundle
        genericBundle = GenericResourceBundle.objects.create()

        gres1 = GenericResource.objects.create(
            bundle=genericBundle,
            name='generic resource ' + str(self.count)
        )
        self.count += 1
        gHost1 = GenericHost.objects.create(
            resource=gres1,
            profile=hostProfile
        )

        gres2 = GenericResource.objects.create(
            bundle=genericBundle,
            name='generic resource ' + str(self.count)
        )
        self.count += 1
        gHost2 = GenericHost.objects.create(
            resource=gres2,
            profile=hostProfile
        )
        user1 = User.objects.create(username='user1')

        add_booking_perm = Permission.objects.get(codename='add_booking')
        user1.user_permissions.add(add_booking_perm)

        user1 = User.objects.get(pk=user1.id)

        conf = ConfigBundle.objects.create(owner=user1, name="test conf")
        self.makeHostConfigurations([gHost1, gHost2], conf)

        # actual resource bundle
        bundle = ResourceBundle.objects.create(
            template=genericBundle
        )

        host1 = Host.objects.create(
            template=gHost1,
            booked=True,
            name='host1',
            bundle=bundle,
            profile=hostProfile,
            lab=lab
        )

        host2 = Host.objects.create(
            template=gHost2,
            booked=True,
            name='host2',
            bundle=bundle,
            profile=hostProfile,
            lab=lab
        )

        vlan1 = Vlan.objects.create(vlan_id=300, tagged=False)
        vlan2 = Vlan.objects.create(vlan_id=300, tagged=False)

        iface1 = Interface.objects.create(
            mac_address='00:11:22:33:44:55',
            bus_address='some bus address',
            switch_name='switch1',
            port_name='port10',
            host=host1
        )

        iface1.config = [vlan1]

        iface2 = Interface.objects.create(
            mac_address='00:11:22:33:44:56',
            bus_address='some bus address',
            switch_name='switch1',
            port_name='port12',
            host=host2
        )

        iface2.config = [vlan2]

        # finally, can create booking
        self.booking = Booking.objects.create(
            owner=user1,
            start=timezone.now(),
            end=timezone.now() + timedelta(weeks=1),
            purpose='Testing',
            resource=bundle,
            config_bundle=conf
        )

        serialized_booking = {}

        host1 = {}
        host1['hostname'] = 'host1'
        host1['image'] = {}  # TODO: Images
        host1['deploy_image'] = True
        host2 = {}
        host2['hostname'] = 'host2'
        host2['image'] = {}  # TODO: Images
        host2['deploy_image'] = True

        serialized_booking['hosts'] = [host1, host2]

        net = {}
        net['name'] = 'network_name'
        net['vlan_id'] = 300
        netHost1 = {}
        netHost1['hostname'] = 'host1'
        netHost1['tagged'] = False
        netHost1['interface'] = 0
        netHost2 = {}
        netHost2['hostname'] = 'host2'
        netHost2['tagged'] = False
        netHost2['interface'] = 0
        net['hosts'] = [netHost1, netHost2]

        serialized_booking['networking'] = [net]
        serialized_booking['jumphost'] = 'host1'

        self.serialized_booking = serialized_booking

    def test_to_representation(self):
        keys = ['hosts', 'networking', 'jumphost']
        serialized_form = self.serializer.to_representation(self.booking)
        for key in keys:
            self.assertEquals(serialized_form[key], self.serialized_booking)
