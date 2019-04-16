##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from dashboard.exceptions import (
    ResourceExistenceException,
    ResourceAvailabilityException,
    ResourceProvisioningException,
    ModelValidationException,
)
from resource_inventory.models import (
    Host,
    HostConfiguration,
    ResourceBundle,
    HostProfile,
    Network,
    Vlan
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

    def getAvailableHostTypes(self, lab):
        hostset = Host.objects.filter(lab=lab).filter(booked=False).filter(working=True)
        hostprofileset = HostProfile.objects.filter(host__in=hostset, labs=lab)
        return set(hostprofileset)

    def hostsAvailable(self, grb):
        """
        This method will check if the given GenericResourceBundle
        is available. No changes to the database
        """

        # count up hosts
        profile_count = {}
        for host in grb.getHosts():
            if host.profile not in profile_count:
                profile_count[host.profile] = 0
            profile_count[host.profile] += 1

        # check that all required hosts are available
        for profile in profile_count.keys():
            available = Host.objects.filter(
                booked=False,
                lab=grb.lab,
                profile=profile
            ).count()
            needed = profile_count[profile]
            if available < needed:
                return False
        return True

    # public interface
    def deleteResourceBundle(self, resourceBundle):
        for host in Host.objects.filter(bundle=resourceBundle):
            self.releaseHost(host)
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

    def convertResourceBundle(self, genericResourceBundle, config=None):
        """
        Takes in a GenericResourceBundle and 'converts' it into a ResourceBundle
        """
        resource_bundle = ResourceBundle.objects.create(template=genericResourceBundle)
        generic_hosts = genericResourceBundle.getHosts()
        physical_hosts = []

        vlan_map = self.get_vlans(genericResourceBundle)

        for generic_host in generic_hosts:
            host_config = None
            if config:
                host_config = HostConfiguration.objects.get(bundle=config, host=generic_host)
            try:
                physical_host = self.acquireHost(generic_host, genericResourceBundle.lab.name)
            except ResourceAvailabilityException:
                self.fail_acquire(physical_hosts, vlan_map)
                raise ResourceAvailabilityException("Could not provision hosts, not enough available")
            try:
                physical_host.bundle = resource_bundle
                physical_host.template = generic_host
                physical_host.config = host_config
                physical_hosts.append(physical_host)

                self.configureNetworking(physical_host, vlan_map)
            except Exception:
                self.fail_acquire(physical_hosts, vlan_map)
                raise ResourceProvisioningException("Network configuration failed.")
            try:
                physical_host.save()
            except Exception:
                self.fail_acquire(physical_hosts)
                raise ModelValidationException("Saving hosts failed")

        return resource_bundle

    def configureNetworking(self, host, vlan_map):
        generic_interfaces = list(host.template.generic_interfaces.all())
        for int_num, physical_interface in enumerate(host.interfaces.all()):
            generic_interface = generic_interfaces[int_num]
            physical_interface.config.clear()
            for connection in generic_interface.connections.all():
                physical_interface.config.add(
                    Vlan.objects.create(
                        vlan_id=vlan_map[connection.network.name],
                        tagged=connection.vlan_is_tagged,
                        public=connection.network.is_public,
                        network=connection.network
                    )
                )

    # private interface
    def acquireHost(self, genericHost, labName):
        host_full_set = Host.objects.filter(lab__name__exact=labName, profile=genericHost.profile)
        if not host_full_set.first():
            raise ResourceExistenceException("No matching servers found")
        host_set = host_full_set.filter(booked=False)
        if not host_set.first():
            raise ResourceAvailabilityException("No unbooked hosts match requested hosts")
        host = host_set.first()
        host.booked = True
        host.template = genericHost
        host.save()
        return host

    def releaseHost(self, host):
        host.template = None
        host.bundle = None
        host.booked = False
        host.save()

    def releaseNetworks(self, grb, vlan_manager, vlans):
        for net_name, vlan_id in vlans.items():
            net = Network.objects.get(name=net_name, bundle=grb)
            if(net.is_public):
                vlan_manager.release_public_vlan(vlan_id)
            else:
                vlan_manager.release_vlans(vlan_id)

    def fail_acquire(self, hosts, vlans):
        grb = hosts[0].template.resource.bundle
        vlan_manager = hosts[0].lab.vlan_manager
        self.releaseNetworks(grb, vlan_manager, vlans)
        for host in hosts:
            self.releaseHost(host)
