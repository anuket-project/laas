##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.utils import timezone

import json
from datetime import timedelta

from booking.models import Booking
from account.models import UserProfile, Lab, LabStatus, VlanManager, PublicNetwork
from resource_inventory.models import (
    ResourceTemplate,
    ResourceProfile,
    ResourceConfiguration,
    InterfaceProfile,
    InterfaceConfiguration,
    Server,
    DiskProfile,
    CpuProfile,
    Opsys,
    Image,
    Scenario,
    Installer,
    OPNFVRole,
    RamProfile,
    Network,
)
from resource_inventory.resource_manager import ResourceManager

"""
Info for make_booking() function:
[topology] argument structure:
    the [topology] argument should describe the structure of the pod
    the top level should be a dictionary, with each key being a hostname
    each value in the top level should be a dictionary with two keys:
        "type" should map to a host profile instance
        "nets" should map to a list of interfaces each with a list of
            dictionaries each defining a network in the format
            { "name": "netname", "tagged": True|False, "public": True|False }
            each network is defined if a matching name is not found

    sample argument structure:
        topology={
            "host1": {
                      "type": instanceOf HostProfile,
                      "role": instanceOf OPNFVRole
                      "image": instanceOf Image
                      "nets": [
                                0: [
                                        0: { "name": "public", "tagged": True, "public": True },
                                        1: { "name": "private", "tagged": False, "public": False },
                                   ]
                                1: []
                              ]
                  }
        }
"""


def make_booking(owner=None, start=timezone.now(),
                 end=timezone.now() + timedelta(days=1),
                 lab=None, purpose="my_purpose",
                 project="my_project", collaborators=[],
                 topology={}, installer=None, scenario=None):

    resource_template = make_resource_template()
    resource = ResourceManager.getInstance().convertResourceBundle(resource_template)
    if not resource:
        raise Exception("Resource not created")

    return Booking.objects.create(
        resource=resource,
        start=start,
        end=end,
        owner=owner,
        purpose=purpose,
        project=project,
        lab=lab,
    )


def make_network(name, lab, grb, public):
    network = Network(name=name, bundle=grb, is_public=public)
    if public:
        public_net = lab.vlan_manager.get_public_vlan()
        if not public_net:
            raise Exception("No more public networks available")
        lab.vlan_manager.reserve_public_vlan(public_net.vlan)
        network.vlan_id = public_net.vlan
    else:
        private_net = lab.vlan_manager.get_vlan()
        if not private_net:
            raise Exception("No more generic vlans are available")
        lab.vlan_manager.reserve_vlans([private_net])
        network.vlan_id = private_net

    network.save()
    return network


def make_resource_template(owner=None, lab=None, name="Test Template"):
    if owner is None:
        owner = make_user(username="template_owner")
    if lab is None:
        lab = make_lab(name="template_lab")
    rt = ResourceTemplate.objects.create(name=name, owner=owner, lab=lab, public=True)
    config = make_resource_config(rt)
    make_interface_config(config)
    return rt


def make_resource_config(template, profile=None, image=None):
    if profile is None:
        profile = make_resource_profile(lab=template.lab)

    if image is None:
        image = make_image(profile)

    return ResourceConfiguration.objects.create(profile=profile, image=image, template=template)


def make_interface_config(resource_config):
    # lets just grab one of the iface profiles from the related host
    iface_profile = resource_config.profile.interfaceprofile.all()[0]

    # not adding any connections here
    return InterfaceConfiguration.objects.create(profile=iface_profile, resource_config=resource_config)


def make_user(is_superuser=False, username="testuser",
              password="testpassword", email="default_email@user.com"):
    user = User.objects.get_or_create(username=username, email=email, password=password)[0]

    user.is_superuser = is_superuser
    user.save()

    return user


def make_user_profile(user=None, email_addr="email@email.com",
                      company="company", full_name="John Doe",
                      booking_privledge=True, ssh_file=None):
    user = user or make_user()
    profile = UserProfile.objects.get_or_create(
        email_addr=email_addr,
        company=company,
        full_name=full_name,
        booking_privledge=booking_privledge,
        user=user
    )[0]
    profile.ssh_public_key.save("user_ssh_key", ssh_file if ssh_file else ContentFile("public key content string"))

    return profile


def make_vlan_manager(vlans=None, block_size=20, allow_overlapping=False, reserved_vlans=None):
    if not vlans:
        vlans = [vlan % 2 for vlan in range(4095)]
    if not reserved_vlans:
        reserved_vlans = [0 for i in range(4095)]

    return VlanManager.objects.create(
        vlans=json.dumps(vlans),
        reserved_vlans=json.dumps(vlans),
        block_size=block_size,
        allow_overlapping=allow_overlapping
    )


def make_lab(user=None, name="Test_Lab_Instance",
             status=LabStatus.UP, vlan_manager=None,
             pub_net_count=5):
    if not vlan_manager:
        vlan_manager = make_vlan_manager()

    if not user:
        user = make_user(username=name + " user")

    lab = Lab.objects.create(
        lab_user=user,
        name=name,
        contact_email='test_lab@test_site.org',
        contact_phone='603 123 4567',
        status=status,
        vlan_manager=vlan_manager,
        description='test lab instantiation',
        api_token='12345678'
    )

    for i in range(pub_net_count):
        make_public_net(vlan=i * 2 + 1, lab=lab)

    return lab


"""
resource_inventory instantiation section for permanent resources
"""


def make_resource_profile(lab, name="test_hostprofile"):
    resource_profile = ResourceProfile.objects.create(
        name=name,
        description='test resourceprofile instance'
    )
    resource_profile.labs.add(lab)

    RamProfile.objects.create(host=resource_profile, amount=8, channels=2)
    CpuProfile.objects.create(cores=4, architecture="x86_64", cpus=1, host=resource_profile)
    DiskProfile.objects.create(
        name="test disk profile",
        size=256,
        media_type="SSD",
        host=resource_profile
    )

    InterfaceProfile.objects.create(
        host=resource_profile,
        name="test interface profile",
        speed=1000,
        nic_type="pcie"
    )

    return resource_profile


def make_image(resource_profile, lab=None, lab_id="4", owner=None, os=None,
               public=True, name="default image", description="default image"):
    if lab is None:
        lab = make_lab()

    if owner is None:
        owner = make_user()

    if os is None:
        os = make_os()

    return Image.objects.create(
        from_lab=lab,
        lab_id=lab_id,
        os=os,
        host_type=resource_profile,
        public=public,
        name=name,
        description=description
    )


def make_scenario(name="test scenario"):
    return Scenario.objects.create(name=name)


def make_installer(scenarios, name="test installer"):
    installer = Installer.objects.create(name=name)
    for scenario in scenarios:
        installer.sup_scenarios.add(scenario)

    return installer


def make_os(installers=None, name="test OS"):
    if not installers:
        installers = [make_installer([make_scenario()])]
    os = Opsys.objects.create(name=name)
    for installer in installers:
        os.sup_installers.add(installer)

    return os


def make_server(host_profile, lab, labid="test_host", name="test_host",
                booked=False, working=True, config=None, template=None,
                bundle=None, model="Model 1", vendor="ACME"):
    return Server.objects.create(
        lab=lab,
        profile=host_profile,
        name=name,
        booked=booked,
        working=working,
        config=config,
        template=template,
        bundle=bundle,
        model=model,
        vendor=vendor
    )


def make_opnfv_role(name="Jumphost", description="test opnfvrole"):
    return OPNFVRole.objects.create(
        name=name,
        description=description
    )


def make_public_net(vlan, lab, in_use=False,
                    cidr="0.0.0.0/0", gateway="0.0.0.0"):
    return PublicNetwork.objects.create(
        lab=lab,
        vlan=vlan,
        cidr=cidr,
        gateway=gateway
    )
