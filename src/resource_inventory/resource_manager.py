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
from resource_inventory.models import Host, HostConfiguration, ResourceBundle, HostProfile


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

    def convertResourceBundle(self, genericResourceBundle, lab=None, config=None):
        """
        Takes in a GenericResourceBundle and 'converts' it into a ResourceBundle
        """
        resource_bundle = ResourceBundle()
        resource_bundle.template = genericResourceBundle
        resource_bundle.save()

        hosts = genericResourceBundle.getHosts()

        # current supported case: user creating new booking
        # currently unsupported: editing existing booking

        physical_hosts = []

        for host in hosts:
            host_config = None
            if config:
                host_config = HostConfiguration.objects.get(bundle=config, host=host)
            try:
                physical_host = self.acquireHost(host, genericResourceBundle.lab.name)
            except ResourceAvailabilityException:
                self.fail_acquire(physical_hosts)
                raise ResourceAvailabilityException("Could not provision hosts, not enough available")
            try:
                physical_host.bundle = resource_bundle
                physical_host.template = host
                physical_host.config = host_config
                physical_hosts.append(physical_host)

                self.configureNetworking(physical_host)
            except Exception:
                self.fail_acquire(physical_hosts)
                raise ResourceProvisioningException("Network configuration failed.")
            try:
                physical_host.save()
            except Exception:
                self.fail_acquire(physical_hosts)
                raise ModelValidationException("Saving hosts failed")

        return resource_bundle

    def configureNetworking(self, host):
        generic_interfaces = list(host.template.generic_interfaces.all())
        for int_num, physical_interface in enumerate(host.interfaces.all()):
            generic_interface = generic_interfaces[int_num]
            physical_interface.config.clear()
            for vlan in generic_interface.vlans.all():
                physical_interface.config.add(vlan)

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

    def fail_acquire(self, hosts):
        for host in hosts:
            self.releaseHost(host)
