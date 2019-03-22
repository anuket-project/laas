##############################################################################
# Copyright (c) 2019 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from resource_inventory.models import Host, Vlan
from account.models import Lab
from booking.models import Booking
from datetime import timedelta
from django.utils import timezone


def free_leaked_hosts(free_old_bookings=False, old_booking_age=timedelta(days=1)):
    bundles = [booking.resource for booking in Booking.objects.filter(end__gt=timezone.now())]
    active_hosts = set()
    for bundle in bundles:
        active_hosts.update([host for host in bundle.hosts.all()])

    marked_hosts = set(Host.objects.filter(booked=True))

    for host in (marked_hosts - active_hosts):
        host.booked = False
        host.save()


def free_leaked_public_vlans():
    booked_host_interfaces = []

    for lab in Lab.objects.all():

        for host in Host.objects.filter(booked=True).filter(lab=lab):
            for interface in host.interfaces.all():
                booked_host_interfaces.append(interface)

        in_use_vlans = Vlan.objects.filter(public=True).distinct('vlan_id').filter(interface__in=booked_host_interfaces)

        manager = lab.vlan_manager

        for vlan in Vlan.objects.all():
            if vlan not in in_use_vlans:
                if vlan.public:
                    manager.release_public_vlan(vlan.vlan_id)
                manager.release_vlans(vlan)
