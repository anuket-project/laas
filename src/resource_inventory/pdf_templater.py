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
from resource_inventory.models import Host, InterfaceProfile


class PDFTemplater:
    """
    Utility class to create a full PDF yaml file
    """

    @classmethod
    def makePDF(cls, resource):
        """
        fills the pod descriptor file template with info about the resource
        """
        template = "dashboard/pdf.yaml"
        info = {}
        info['details'] = cls.get_pdf_details(resource)
        info['jumphost'] = cls.get_pdf_jumphost(resource)
        info['nodes'] = cls.get_pdf_nodes(resource)

        return render_to_string(template, context=info)

    @classmethod
    def get_pdf_details(cls, resource):
        """
        Info for the "details" section
        """
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

        details['contact'] = email
        details['lab'] = lab
        details['link'] = link
        details['owner'] = owner
        details['location'] = location
        details['type'] = pod_type

        return details

    @classmethod
    def get_pdf_jumphost(cls, resource):
        """
        returns a dict of all the info for the "jumphost" section
        """
        jumphost = Host.objects.get(bundle=resource, config__opnfvRole__name__iexact="jumphost")
        jumphost_info = cls.get_pdf_host(jumphost)
        remote_params = jumphost_info['remote_management']  # jumphost has extra block not in normal hosts
        remote_params.pop("address")
        remote_params.pop("mac_address")
        jumphost_info['remote_params'] = remote_params
        jumphost_info['os'] = jumphost.config.image.os.name
        return jumphost_info

    @classmethod
    def get_pdf_nodes(cls, resource):
        """
        returns a list of all the "nodes" (every host except jumphost)
        """
        pdf_nodes = []
        nodes = Host.objects.filter(bundle=resource).exclude(config__opnfvRole__name__iexact="jumphost")
        for node in nodes:
            pdf_nodes.append(cls.get_pdf_host(node))

        return pdf_nodes

    @classmethod
    def get_pdf_host(cls, host):
        """
        method to gather all needed info about a host
        returns a dict
        """
        host_info = {}
        host_info['name'] = host.template.resource.name
        host_info['node'] = cls.get_pdf_host_node(host)
        host_info['disks'] = []
        for disk in host.profile.storageprofile.all():
            host_info['disks'].append(cls.get_pdf_host_disk(disk))

        host_info['interfaces'] = []
        for interface in host.interfaces.all():
            host_info['interfaces'].append(cls.get_pdf_host_iface(interface))

        host_info['remote_management'] = cls.get_pdf_host_remote_management(host)

        return host_info

    @classmethod
    def get_pdf_host_node(cls, host):
        """
        returns "node" info for a given host
        """
        d = {}
        d['type'] = "baremetal"
        d['vendor'] = host.vendor
        d['model'] = host.model
        d['memory'] = str(host.profile.ramprofile.first().amount) + "G"

        cpu = host.profile.cpuprofile.first()
        d['arch'] = cpu.architecture
        d['cpus'] = cpu.cpus
        d['cores'] = cpu.cores
        cflags = cpu.cflags
        if cflags and cflags.strip():
            d['cpu_cflags'] = cflags
        else:
            d['cpu_cflags'] = "none"

        return d

    @classmethod
    def get_pdf_host_disk(cls, disk):
        """
        returns a dict describing the given disk
        """
        disk_info = {}
        disk_info['name'] = disk.name
        disk_info['capacity'] = str(disk.size) + "G"
        disk_info['type'] = disk.media_type
        disk_info['interface'] = disk.interface
        disk_info['rotation'] = disk.rotation
        return disk_info

    @classmethod
    def get_pdf_host_iface(cls, interface):
        """
        returns a dict describing given interface
        """
        iface_info = {}
        iface_info['features'] = "none"
        iface_info['mac_address'] = interface.mac_address
        iface_info['name'] = interface.name
        profile = InterfaceProfile.objects.get(host=interface.host.profile, name=interface.name)
        iface_info['speed'] = str(int(profile.speed / 1000)) + "gb"
        return iface_info

    @classmethod
    def get_pdf_host_remote_management(cls, host):
        """
        gives the remote params of the host
        """
        mgmt = {}
        mgmt['address'] = "I dunno"
        mgmt['mac_address'] = "I dunno"
        mgmt['pass'] = "I dunno"
        mgmt['type'] = "I dunno"
        mgmt['user'] = "I dunno"
        mgmt['versions'] = ["I dunno"]
        return mgmt
