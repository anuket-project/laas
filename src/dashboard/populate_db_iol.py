##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

import json
import yaml

from account.models import Lab, UserProfile
from django.contrib.auth.models import User
from resource_inventory.models import (
    HostProfile,
    InterfaceProfile,
    DiskProfile,
    CpuProfile,
    RamProfile,
    VlanManager,
    Scenario,
    Installer,
    Opsys,
    OPNFVRole,
    Image,
    Interface,
    Host
)


class Populator:

    def __init__(self):
        self.host_profile_count = 0
        self.generic_host_count = 0
        self.host_profiles = []
        self.generic_bundle_count = 0
        self.booking_count = 0

    def make_host_profile(self, lab, data):
        hostProfile = HostProfile.objects.create(
            host_type=data['host']['type'],
            name=data['host']['name'],
            description=data['host']['description']
        )
        hostProfile.save()

        for iface_data in data['interfaces']:

            interfaceProfile = InterfaceProfile.objects.create(
                speed=iface_data['speed'],
                name=iface_data['name'],
                host=hostProfile
            )
            interfaceProfile.save()

        for disk_data in data['disks']:

            diskProfile = DiskProfile.objects.create(
                size=disk_data['size'],
                media_type=disk_data['type'],
                name=disk_data['name'],
                host=hostProfile
            )
            diskProfile.save()

        cpuProfile = CpuProfile.objects.create(
            cores=data['cpu']['cores'],
            architecture=data['cpu']['arch'],
            cpus=data['cpu']['cpus'],
            host=hostProfile
        )
        cpuProfile.save()
        ramProfile = RamProfile.objects.create(
            amount=data['ram']['amount'],
            channels=data['ram']['channels'],
            host=hostProfile
        )
        ramProfile.save()
        hostProfile.labs.add(lab)
        return hostProfile

    def make_users(self):
        user_pberberian = User.objects.create(username="pberberian")
        user_pberberian.save()
        user_pberberian_prof = UserProfile.objects.create(user=user_pberberian)
        user_pberberian_prof.save()

        user_sbergeron = User.objects.create(username="sbergeron")
        user_sbergeron.save()
        user_sbergeron_prof = UserProfile.objects.create(user=user_sbergeron)
        user_sbergeron_prof.save()
        return [user_sbergeron, user_pberberian]

    def make_labs(self):
        unh_iol = User.objects.create(username="unh_iol")
        unh_iol.save()
        vlans = []
        reserved = []
        for i in range(1, 4096):
            vlans.append(1)
            reserved.append(0)
        iol = Lab.objects.create(
            lab_user=unh_iol,
            name="UNH_IOL",
            vlan_manager=VlanManager.objects.create(
                vlans=json.dumps(vlans),
                reserved_vlans=json.dumps(reserved),
                allow_overlapping=False,
                block_size=20,
            ),
            api_token=Lab.make_api_token(),
            contact_email="nfv-lab@iol.unh.edu",
            location="University of New Hampshire, Durham NH, 03824 USA"
        )
        return [iol]

    def make_configurations(self):
        # scenarios
        scen1 = Scenario.objects.create(name="os-nosdn-nofeature-noha")
        scen2 = Scenario.objects.create(name="os-odl-kvm-ha")
        scen3 = Scenario.objects.create(name="os-nosdn-nofeature-ha")

        # installers
        fuel = Installer.objects.create(name="Fuel")
        fuel.sup_scenarios.add(scen1)
        fuel.sup_scenarios.add(scen3)
        fuel.save()
        joid = Installer.objects.create(name="Joid")
        joid.sup_scenarios.add(scen1)
        joid.sup_scenarios.add(scen2)
        joid.save()
        apex = Installer.objects.create(name="Apex")
        apex.sup_scenarios.add(scen2)
        apex.sup_scenarios.add(scen3)
        apex.save()
        daisy = Installer.objects.create(name="Daisy")
        daisy.sup_scenarios.add(scen1)
        daisy.sup_scenarios.add(scen2)
        daisy.sup_scenarios.add(scen3)
        daisy.save()
        compass = Installer.objects.create(name="Compass")
        compass.sup_scenarios.add(scen1)
        compass.sup_scenarios.add(scen3)
        compass.save()

        # operating systems
        ubuntu = Opsys.objects.create(name="Ubuntu")
        ubuntu.sup_installers.add(compass)
        ubuntu.sup_installers.add(joid)
        ubuntu.save()
        centos = Opsys.objects.create(name="CentOs")
        centos.sup_installers.add(apex)
        centos.sup_installers.add(fuel)
        centos.save()
        suse = Opsys.objects.create(name="Suse")
        suse.sup_installers.add(fuel)
        suse.save()

        # opnfv roles
        OPNFVRole.objects.create(name="Compute", description="Does the heavy lifting")
        OPNFVRole.objects.create(name="Controller", description="Controls everything")
        OPNFVRole.objects.create(name="Jumphost", description="Entry Point")

        lab = Lab.objects.first()
        user = UserProfile.objects.first().user
        Image.objects.create(
            lab_id=23,
            name="hpe centos",
            from_lab=lab,
            owner=user,
            host_type=HostProfile.objects.get(name="hpe")
        )
        Image.objects.create(
            lab_id=25,
            name="hpe ubuntu",
            from_lab=lab,
            owner=user,
            host_type=HostProfile.objects.get(name="hpe")
        )

        Image.objects.create(
            lab_id=26,
            name="hpe suse",
            from_lab=lab,
            owner=user,
            host_type=HostProfile.objects.get(name="hpe")
        )

        Image.objects.create(
            lab_id=27,
            name="arm ubuntu",
            from_lab=lab,
            owner=user,
            host_type=HostProfile.objects.get(name="arm")
        )

    def make_lab_hosts(self, hostcount, profile, lab, data, offset=1):
        for i in range(hostcount):
            name = "Host_" + lab.name + "_" + profile.name + "_" + str(i + offset)
            host = Host.objects.create(
                name=name,
                lab=lab,
                profile=profile,
                labid=data[i]['labid']
            )
            for iface_profile in profile.interfaceprofile.all():
                iface_data = data[i]['interfaces'][iface_profile.name]
                Interface.objects.create(
                    mac_address=iface_data['mac'],
                    bus_address=iface_data['bus'],
                    name=iface_profile.name,
                    host=host
                )

    def make_profile_data(self):
        """
        returns a dictionary of data from the yaml files
        created by inspection scripts
        """
        data = []
        for prof in ["hpe", "arm"]:  # TODO
            profile_dict = {}
            host = {
                "name": prof,
                "type": 0,
                "description": "some LaaS servers"
            }
            profile_dict['host'] = host
            profile_dict['interfaces'] = []
            for interface in [{"name": "eno1", "speed": 1000}, {"name": "eno2", "speed": 10000}]:  # TODO
                iface_dict = {}
                iface_dict["name"] = interface['name']
                iface_dict['speed'] = interface['speed']
                profile_dict['interfaces'].append(iface_dict)

            profile_dict['disks'] = []
            for disk in [{"size": 1000, "type": "ssd", "name": "sda"}]:  # TODO
                disk_dict = {}
                disk_dict['size'] = disk['size']
                disk_dict['type'] = disk['type']
                disk_dict['name'] = disk['name']
                profile_dict['disks'].append(disk_dict)

            # cpu
            cpu = {}
            cpu['cores'] = 4
            cpu['arch'] = "x86"
            cpu['cpus'] = 2
            profile_dict['cpu'] = cpu

            # ram
            ram = {}
            ram['amount'] = 256
            ram['channels'] = 4
            profile_dict['ram'] = ram

            data.append(profile_dict)

        return data

    def get_lab_data(self, lab):
        data = {}
        path = "/pharos_dashboard/data/" + lab.name + "/"
        host_file = open(path + "hostlist.json")
        host_structure = json.loads(host_file.read())
        host_file.close()
        for profile in host_structure['profiles'].keys():
            data[profile] = {}
            prof_path = path + profile
            for host in host_structure['profiles'][profile]:
                host_file = open(prof_path + "/" + host + ".yaml")
                host_data = yaml.load(host_file.read())
                host_file.close()
                data[profile][host] = host_data
        return data

    def make_profiles_and_hosts(self, lab, lab_data):
        for host_profile_name, host_data_dict in lab_data.items():
            if len(host_data_dict) < 1:
                continue
            host_profile = HostProfile.objects.create(
                name=host_profile_name,
                description=""
            )
            host_profile.labs.add(lab)
            example_host_data = list(host_data_dict.values())[0]

            cpu_data = example_host_data['cpu']
            CpuProfile.objects.create(
                cores=cpu_data['cores'],
                architecture=cpu_data['arch'],
                cpus=cpu_data['cpus'],
                host=host_profile
            )

            ram_data = example_host_data['memory']
            RamProfile.objects.create(
                amount=int(ram_data[:-1]),
                channels=1,
                host=host_profile
            )

            disks_data = example_host_data['disk']
            for disk_data in disks_data:
                size = 0
                try:
                    size = int(disk_data['size'].split('.')[0])
                except Exception:
                    size = int(disk_data['size'].split('.')[0][:-1])
                DiskProfile.objects.create(
                    size=size,
                    media_type="SSD",
                    name=disk_data['name'],
                    host=host_profile
                )

            ifaces_data = example_host_data['interface']
            for iface_data in ifaces_data:
                InterfaceProfile.objects.create(
                    speed=iface_data['speed'],
                    name=iface_data['name'],
                    host=host_profile
                )

            # all profiles created
            for hostname, host_data in host_data_dict.items():
                host = Host.objects.create(
                    name=hostname,
                    labid=hostname,
                    profile=host_profile,
                    lab=lab
                )
                for iface_data in host_data['interface']:
                    Interface.objects.create(
                        mac_address=iface_data['mac'],
                        bus_address=iface_data['busaddr'],
                        name=iface_data['name'],
                        host=host
                    )

    def populate(self):
        self.labs = self.make_labs()
        # We should use the existing users, not creating our own
        for lab in self.labs:
            lab_data = self.get_lab_data(lab)
            self.make_profiles_and_hosts(lab, lab_data)

        # We will add opnfv info and images as they are created and supported
