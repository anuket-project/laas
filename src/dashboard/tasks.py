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
from booking.models import Booking
from notifier.manager import NotificationHandler
from api.models import (
    Job,
    JobStatus,
    SoftwareRelation,
    HostHardwareRelation,
    HostNetworkRelation,
    AccessRelation,
    JobFactory
)

from resource_inventory.resource_manager import ResourceManager
from resource_inventory.models import ConfigState


@shared_task
def booking_poll():
    def cleanup_resource_task(qs):
        for hostrelation in qs:
            hostrelation.config.state = ConfigState.CLEAN
            hostrelation.config.save()
            hostrelation.status = JobStatus.NEW
            hostrelation.save()

    def cleanup_software(qs):
        if qs.exists():
            relation = qs.first()
            software = relation.config.opnfv
            software.clear_delta()
            software.save()
            relation.status = JobStatus.NEW
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
            cleanup_resource_task(HostHardwareRelation.objects.filter(job=job))
            cleanup_resource_task(HostNetworkRelation.objects.filter(job=job))
            cleanup_access(AccessRelation.objects.filter(job=job))
            job.complete = True
            job.save()
            NotificationHandler.notify_booking_end(booking)


@shared_task
def free_hosts():
    """Free all hosts that should be freed."""
    undone_statuses = [JobStatus.NEW, JobStatus.CURRENT, JobStatus.ERROR]
    undone_jobs = Job.objects.filter(
        hostnetworkrelation__status__in=undone_statuses,
        hosthardwarerelation__status__in=undone_statuses
    )

    bookings = Booking.objects.exclude(
        job__in=undone_jobs
    ).filter(
        end__lt=timezone.now(),
        job__complete=True,
        resource__isnull=False
    )
    for booking in bookings:
        ResourceManager.getInstance().releaseResourceBundle(booking.resource)


@shared_task
def query_vpn_users():
    """ get active vpn users """
    JobFactory.makeActiveUsersTask()
