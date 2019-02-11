##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.contrib.auth.models import User

import json

from account.models import UserProfile, Lab, LabStatus, VlanManager, PublicNetwork
from resource_inventory.models import (
    Host,
    HostProfile,
    InterfaceProfile,
    DiskProfile,
    CpuProfile,
    Opsys,
    Image,
    Scenario,
    Installer,
    OPNFVRole,
    RamProfile,
)


class BookingContextData(object):
    def prepopulate(self, *args, **kwargs):
        self.loginuser = instantiate_user(False, username=kwargs.get("login_username", "newtestuser"), password="testpassword")
        instantiate_userprofile(self.loginuser, True)

        lab_user = kwargs.get("lab_user", instantiate_user(True))
        self.lab = instantiate_lab(lab_user)

        self.host_profile = make_hostprofile_set(self.lab)
        self.scenario = instantiate_scenario()
        self.installer = instantiate_installer([self.scenario])
        os = instantiate_os([self.installer])
        self.image = instantiate_image(self.lab, 1, self.loginuser, os, self.host_profile)
        self.host = instantiate_host(self.host_profile, self.lab)
        self.role = instantiate_opnfvrole()
        self.pubnet = instantiate_publicnet(10, self.lab)


def instantiate_user(is_superuser,
                     username="testuser",
                     password="testpassword",
                     email="default_email@user.com"
                     ):
    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_superuser = is_superuser

    user.save()

    return user


def instantiate_userprofile(user=None, can_book_multiple=False):
    if not user:
        user = instantiate_user(True, 'test_user', 'test_pass', 'test_user@test_site.org')
    userprofile = UserProfile()
    userprofile.user = user
    userprofile.booking_privledge = can_book_multiple

    userprofile.save()

    return user


def instantiate_vlanmanager(vlans=None,
                            block_size=20,
                            allow_overlapping=False,
                            reserved_vlans=None
                            ):
    vlanmanager = VlanManager()
    if not vlans:
        vlans = []
        for vlan in range(0, 4095):
            vlans.append(vlan % 2)
    vlanmanager.vlans = json.dumps(vlans)
    if not reserved_vlans:
        reserved_vlans = []
        for vlan in range(0, 4095):
            reserved_vlans.append(0)
    vlanmanager.reserved_vlans = json.dumps(vlans)
    vlanmanager.block_size = block_size
    vlanmanager.allow_overlapping = allow_overlapping

    vlanmanager.save()

    return vlanmanager


def instantiate_lab(user=None,
                    name="Test Lab Instance",
                    status=LabStatus.UP,
                    vlan_manager=None
                    ):
    if not vlan_manager:
        vlan_manager = instantiate_vlanmanager()

    if not user:
        user = instantiate_user(True, 'test_user', 'test_pass', 'test_user@test_site.org')

    lab = Lab()
    lab.lab_user = user
    lab.name = name
    lab.contact_email = 'test_lab@test_site.org'
    lab.contact_phone = '603 123 4567'
    lab.status = status
    lab.vlan_manager = vlan_manager
    lab.description = 'test lab instantiation'
    lab.api_token = '12345678'

    lab.save()

    return lab


"""
resource_inventory instantiation section for permenant resources
"""


def make_hostprofile_set(lab, name="test_hostprofile"):
    hostprof = instantiate_hostprofile(lab, name=name)
    instantiate_diskprofile(hostprof, 500, name=name)
    instantiate_cpuprofile(hostprof)
    instantiate_interfaceprofile(hostprof, name=name)
    instantiate_ramprofile(hostprof)

    return hostprof


def instantiate_hostprofile(lab,
                            host_type=0,
                            name="test hostprofile instance"
                            ):
    hostprof = HostProfile()
    hostprof.host_type = host_type
    hostprof.name = name
    hostprof.description = 'test hostprofile instance'
    hostprof.save()
    hostprof.labs.add(lab)

    hostprof.save()

    return hostprof


def instantiate_ramprofile(host,
                           channels=4,
                           amount=256):
    ramprof = RamProfile()
    ramprof.host = host
    ramprof.amount = amount
    ramprof.channels = channels
    ramprof.save()

    return ramprof


def instantiate_diskprofile(hostprofile,
                            size=0,
                            media_type="SSD",
                            name="test diskprofile",
                            rotation=0,
                            interface="sata"):

    diskprof = DiskProfile()
    diskprof.name = name
    diskprof.size = size
    diskprof.media_type = media_type
    diskprof.host = hostprofile
    diskprof.rotation = rotation
    diskprof.interface = interface

    diskprof.save()

    return diskprof


def instantiate_cpuprofile(hostprofile,
                           cores=4,
                           architecture="x86_64",
                           cpus=4,
                           ):
    cpuprof = CpuProfile()
    cpuprof.cores = cores
    cpuprof.architecture = architecture
    cpuprof.cpus = cpus
    cpuprof.host = hostprofile
    cpuprof.cflags = ''

    cpuprof.save()

    return cpuprof


def instantiate_interfaceprofile(hostprofile,
                                 speed=1000,
                                 name="test interface profile",
                                 nic_type="pcie"
                                 ):
    intprof = InterfaceProfile()
    intprof.host = hostprofile
    intprof.name = name
    intprof.speed = speed
    intprof.nic_type = nic_type

    intprof.save()

    return intprof


def instantiate_image(lab,
                      lab_id,
                      owner,
                      os,
                      host_profile,
                      public=True,
                      name="default image",
                      description="default image"
                      ):
    image = Image()
    image.from_lab = lab
    image.lab_id = lab_id
    image.os = os
    image.host_type = host_profile
    image.public = public
    image.name = name
    image.description = description

    image.save()

    return image


def instantiate_scenario(name="test scenario"):
    scenario = Scenario()
    scenario.name = name
    scenario.save()
    return scenario


def instantiate_installer(supported_scenarios,
                          name="test installer"
                          ):
    installer = Installer()
    installer.name = name
    installer.save()
    for scenario in supported_scenarios:
        installer.sup_scenarios.add(scenario)

    installer.save()
    return installer


def instantiate_os(supported_installers,
                   name="test operating system",
                   ):
    os = Opsys()
    os.name = name
    os.save()
    for installer in supported_installers:
        os.sup_installers.add(installer)
    os.save()
    return os


def instantiate_host(host_profile,
                     lab,
                     labid="test_host",
                     name="test_host",
                     booked=False,
                     working=True,
                     config=None,
                     template=None,
                     bundle=None,
                     model="Model 1",
                     vendor="ACME"):
    host = Host()
    host.lab = lab
    host.profile = host_profile
    host.name = name
    host.booked = booked
    host.working = working
    host.config = config
    host.template = template
    host.bundle = bundle
    host.model = model
    host.vendor = vendor

    host.save()

    return host


def instantiate_opnfvrole(name="Jumphost",
                          description="test opnfvrole"):
    role = OPNFVRole()
    role.name = name
    role.description = description
    role.save()

    return role


def instantiate_publicnet(vlan,
                          lab,
                          in_use=False,
                          cidr="0.0.0.0/0",
                          gateway="0.0.0.0"):
    pubnet = PublicNetwork()
    pubnet.lab = lab
    pubnet.vlan = vlan
    pubnet.cidr = cidr
    pubnet.gateway = gateway
    pubnet.save()

    return pubnet
