##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.template.loader import render_to_string

import booking
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

    def makePDF(self, resource):
        """
        fills the pod descriptor file template with info about the resource
        """
        template = "dashboard/pdf.yaml"
        info = {}
        info['details'] = self.get_pdf_details(resource)
        info['jumphost'] = self.get_pdf_jumphost(resource)
        info['nodes'] = self.get_pdf_nodes(resource)

        return render_to_string(template, context=info)

    def get_pdf_details(self, resource):
        details = {}
        owner = "Anon"
        email = "email@mail.com"
        resource_lab = resource.template.lab
        lab = resource_lab.name
        location = resource_lab.location
        pod_type = "development"
        link = "https://wiki.opnfv.org/display/INF/Pharos+Laas"

        try:
            # try to get more specific info that may fail, we dont care if it does
            booking_owner = booking.models.Booking.objects.get(resource=resource).owner
            owner = booking_owner.username
            email = booking_owner.userprofile.email_addr
        except Exception:
            pass

        details['owner'] = owner
        details['email'] = email
        details['lab'] = lab
        details['location'] = location
        details['type'] = pod_type
        details['link'] = link

        return details

    def get_pdf_jumphost(self, resource):
        jumphost = Host.objects.get(bundle=resource, config__opnfvRole__name__iexact="jumphost")
        return self.get_pdf_host(jumphost)

    def get_pdf_nodes(self, resource):
        pdf_nodes = []
        nodes = Host.objects.filter(bundle=resource).exclude(config__opnfvRole__name__iexact="jumphost")
        for node in nodes:
            pdf_nodes.append(self.get_pdf_host(node))

        return pdf_nodes

    def get_pdf_host(self, host):
        host_info = {}
        host_info['name'] = host.template.resource.name
        host_info['node'] = {}
        host_info['node']['type'] = "baremetal"
        host_info['node']['vendor'] = host.vendor
        host_info['node']['model'] = host.model
        host_info['node']['arch'] = host.profile.cpuprofile.first().architecture
        host_info['node']['cpus'] = host.profile.cpuprofile.first().cpus
        host_info['node']['cores'] = host.profile.cpuprofile.first().cores
        cflags = host.profile.cpuprofile.first().cflags
        if cflags and cflags.strip():
            host_info['node']['cpu_cflags'] = cflags
        host_info['node']['memory'] = str(host.profile.ramprofile.first().amount) + "G"
        host_info['disks'] = []
        for disk in host.profile.storageprofile.all():
            disk_info = {}
            disk_info['name'] = disk.name
            disk_info['capacity'] = str(disk.size) + "G"
            disk_info['type'] = disk.media_type
            disk_info['interface'] = disk.interface
            disk_info['rotation'] = disk.rotation
            host_info['disks'].append(disk_info)

        host_info['interfaces'] = []
        for interface in host.interfaces.all():
            iface_info = {}
            iface_info['name'] = interface.name
            iface_info['address'] = "unknown"
            iface_info['mac_address'] = interface.mac_address
            vlans = "|".join([str(vlan.vlan_id) for vlan in interface.config.all()])
            iface_info['vlans'] = vlans
            host_info['interfaces'].append(iface_info)

        return host_info
