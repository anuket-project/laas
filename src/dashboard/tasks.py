##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from booking.models import Booking
from notifier.manager import NotificationHandler
from api.models import *
from resource_inventory.resource_manager import ResourceManager


@shared_task
def booking_poll():
    def cleanup_hardware(qs):
        for hostrelation in qs:
            config = hostrelation.config
            config.clear_delta()
            config.set_power("off")
            config.save()
            hostrelation.status=JobStatus.NEW
            hostrelation.save()

    def cleanup_network(qs):
        for hostrelation in qs:
            network = hostrelation.config
            network.interfaces.clear()
            host = hostrelation.host
            network.clear_delta()
            vlans = []
            for interface in host.interfaces.all():
                for vlan in interface.config.all():
                    if vlan.public:
                        try:
                            host.lab.vlan_manager.release_public_vlan(vlan.vlan_id)
                        except:  # will fail if we already released in this loop
                            pass
                    else:
                        vlans.append(vlan.vlan_id)

                # release all vlans
                if len(vlans) > 0:
                    host.lab.vlan_manager.release_vlans(vlans)

                interface.config.clear()
                network.add_interface(interface)
                network.save()
            hostrelation.status=JobStatus.NEW
            hostrelation.save()

    def cleanup_software(qs):
        if qs.exists():
            relation = qs.first()
            software = relation.config.opnfv
            software.clear_delta()
            software.save()
            relation.status=JobStatus.NEW
            relation.save()

    def cleanup_access(qs):
        for relation in qs:
            if "vpn" in relation.config.access_type.lower():
                relation.config.set_revoke(True)
                relation.config.save()
                relation.status = JobStatus.NEW
                relation.save()

    cleanup_set = Booking.objects.filter(end__lte=timezone.now()).filter(job__complete=False)

    for booking in cleanup_set:
        if not booking.job.complete:
            job = booking.job
            cleanup_software(SoftwareRelation.objects.filter(job=job))
            cleanup_hardware(HostHardwareRelation.objects.filter(job=job))
            cleanup_network(HostNetworkRelation.objects.filter(job=job))
            cleanup_access(AccessRelation.objects.filter(job=job))
            job.complete = True
            job.save()
            NotificationHandler.notify_booking_end(booking)


@shared_task
def free_hosts():
    """
    gets all hosts from the database that need to be freed and frees them
    """
    networks = ~Q(~Q(job__hostnetworkrelation__status=200))
    hardware = ~Q(~Q(job__hosthardwarerelation__status=200))

    bookings = Booking.objects.filter(
            networks,
            hardware,
            end__lt=timezone.now(),
            job__complete=True,
            resource__isnull=False
            )
    for booking in bookings:
        ResourceManager.getInstance().deleteResourceBundle(booking.resource)
