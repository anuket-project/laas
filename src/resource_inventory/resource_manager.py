##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
import re

from dashboard.exceptions import ResourceAvailabilityException

from resource_inventory.models import (
    ResourceBundle,
    Network,
    Vlan,
    PhysicalNetwork,
)


class ResourceManager:

    instance = None

    def __init__(self):
        pass

    @staticmethod
    def getInstance():
        if ResourceManager.instance is None:
            ResourceManager.instance = ResourceManager()
        return ResourceManager.instance

    def templateIsReservable(self, resource_template):
        """
        Check if the required resources to reserve this template is available.

        No changes to the database
        """
        # count up hosts
        profile_count = {}
        for config in resource_template.getConfigs():
            if config.profile not in profile_count:
                profile_count[config.profile] = 0
            profile_count[config.profile] += 1

        # check that all required hosts are available
        for profile in profile_count.keys():
            available = len(profile.get_resources(lab=resource_template.lab, unreserved=True))
            needed = profile_count[profile]
            if available < needed:
                return False
        return True

    # public interface
    def deleteResourceBundle(self, resourceBundle):
        for resource in resourceBundle.get_resources():
            resource.release()
        resourceBundle.delete()

    def get_vlans(self, genericResourceBundle):
        networks = {}
        vlan_manager = genericResourceBundle.lab.vlan_manager
        for network in genericResourceBundle.networks.all():
            if network.is_public:
                public_net = vlan_manager.get_public_vlan()
                vlan_manager.reserve_public_vlan(public_net.vlan)
                networks[network.name] = public_net.vlan
            else:
                vlan = vlan_manager.get_vlan()
                vlan_manager.reserve_vlans(vlan)
                networks[network.name] = vlan
        return networks

    def instantiateTemplate(self, resource_template, config=None):
        """
        Convert a ResourceTemplate into a ResourceBundle.

        Takes in a ResourceTemplate and reserves all the
        Resources needed and returns a completed ResourceBundle.
        """
        resource_bundle = ResourceBundle.objects.create(template=resource_template)
        res_configs = resource_template.getConfigs()
        resources = []

        vlan_map = self.get_vlans(resource_template)

        for config in res_configs:
            try:
                phys_res = self.acquireHost(config)
                phys_res.bundle = resource_bundle
                phys_res.config = config
                resources.append(phys_res)

                self.configureNetworking(phys_res, vlan_map)
                phys_res.save()

            except Exception as e:
                self.fail_acquire(resources, vlan_map, resource_template)
                raise e

        return resource_bundle

    def configureNetworking(self, host, vlan_map):
        generic_interfaces = list(host.template.generic_interfaces.all())
        for int_num, physical_interface in enumerate(host.interfaces.all()):
            generic_interface = generic_interfaces[int_num]
            physical_interface.config.clear()
            for connection in generic_interface.connections.all():
                physicalNetwork = PhysicalNetwork.objects.create(
                    vlan_id=vlan_map[connection.network.name],
                    generic_network=connection.network
                )
                physical_interface.config.add(
                    Vlan.objects.create(
                        vlan_id=vlan_map[connection.network.name],
                        tagged=connection.vlan_is_tagged,
                        public=connection.network.is_public,
                        network=physicalNetwork
                    )
                )

    # private interface
    def acquireHost(self, resource_config):
        resources = resource_config.profile.get_resources(lab=resource_config.lab, unreserved=True)
        try:
            resource = resources[0]  # TODO: should we randomize and 'load balance' the servers?
            resource.config = resource_config
            resource.reserve()
            return resource
        except IndexError:
            raise ResourceAvailabilityException("No available resources of requested type")

    def releaseNetworks(self, template, vlans):
        vlan_manager = template.lab.vlan_manager
        for net_name, vlan_id in vlans.items():
            net = Network.objects.get(name=net_name, bundle=template)
            if(net.is_public):
                vlan_manager.release_public_vlan(vlan_id)
            else:
                vlan_manager.release_vlans(vlan_id)

    def fail_acquire(self, hosts, vlans, template):
        self.releaseNetworks(template, vlans)
        for host in hosts:
            host.release()


class HostNameValidator(object):
    regex = r'^[A-Za-z0-9][A-Za-z0-9-]*$'
    message = "Hostnames can only contain alphanumeric characters and hyphens (-). Hostnames must start with a letter"
    pattern = re.compile(regex)

    @classmethod
    def is_valid_hostname(cls, hostname):
        return len(hostname) < 65 and cls.pattern.fullmatch(hostname) is not None
