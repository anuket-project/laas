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
from resource_inventory.models import Server, InterfaceProfile


class PDFTemplater:
    """Utility class to create a full PDF yaml file."""

    @classmethod
    def makePDF(cls, booking):
        """Fill the pod descriptor file template with info about the resource."""
        template = "dashboard/pdf.yaml"
        info = {}
        info['details'] = cls.get_pdf_details(booking.resource)
        info['jumphost'] = cls.get_pdf_jumphost(booking)
        info['nodes'] = cls.get_pdf_nodes(booking)

        return render_to_string(template, context=info)

    @classmethod
    def get_pdf_details(cls, resource):
        """Info for the "details" section."""
        details = {}
        owner = "Anon"
        email = "email@mail.com"
        resource_lab = resource.template.lab
        lab = resource_lab.name
        location = resource_lab.location
        pod_type = "development"
        link = "https://wiki.opnfv.org/display/INF/Laas"

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
    def get_jumphost(cls, booking):
        """Return the host designated as the Jumphost for the booking."""
        jumphost = None
        if booking.opnfv_config:
            jumphost_opnfv_config = booking.opnfv_config.host_opnfv_config.get(
                role__name__iexact="jumphost"
            )
            jumphost = booking.resource.hosts.get(config=jumphost_opnfv_config.host_config)
        else:  # if there is no opnfv config, use headnode
            jumphost = Server.objects.filter(
                bundle=booking.resource,
                config__is_head_node=True
            ).first()

        return jumphost

    @classmethod
    def get_pdf_jumphost(cls, booking):
        """Return a dict of all the info for the "jumphost" section."""
        jumphost = cls.get_jumphost(booking)
        jumphost_info = cls.get_pdf_host(jumphost)
        jumphost_info['os'] = jumphost.config.image.os.name
        return jumphost_info

    @classmethod
    def get_pdf_nodes(cls, booking):
        """Return a list of all the "nodes" (every host except jumphost)."""
        pdf_nodes = []
        nodes = set(Server.objects.filter(bundle=booking.resource))
        nodes.discard(cls.get_jumphost(booking))

        for node in nodes:
            pdf_nodes.append(cls.get_pdf_host(node))

        return pdf_nodes

    @classmethod
    def get_pdf_host(cls, host):
        """
        Gather all needed info about a host.

        returns a dictionary
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

        host_info['remote'] = cls.get_pdf_host_remote_management(host)

        return host_info

    @classmethod
    def get_pdf_host_node(cls, host):
        """Return "node" info for a given host."""
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
        """Return a dict describing the given disk."""
        disk_info = {}
        disk_info['name'] = disk.name
        disk_info['capacity'] = str(disk.size) + "G"
        disk_info['type'] = disk.media_type
        disk_info['interface'] = disk.interface
        disk_info['rotation'] = disk.rotation
        return disk_info

    @classmethod
    def get_pdf_host_iface(cls, interface):
        """Return a dict describing given interface."""
        iface_info = {}
        iface_info['features'] = "none"
        iface_info['mac_address'] = interface.mac_address
        iface_info['name'] = interface.name
        speed = "unknown"
        try:
            profile = InterfaceProfile.objects.get(host=interface.host.profile, name=interface.name)
            speed = str(int(profile.speed / 1000)) + "gb"
        except Exception:
            pass
        iface_info['speed'] = speed
        return iface_info

    @classmethod
    def get_pdf_host_remote_management(cls, host):
        """Get the remote params of the host."""
        man = host.remote_management
        mgmt = {}
        mgmt['address'] = man.address
        mgmt['mac_address'] = man.mac_address
        mgmt['pass'] = man.password
        mgmt['type'] = man.management_type
        mgmt['user'] = man.user
        mgmt['versions'] = [man.versions]
        return mgmt
