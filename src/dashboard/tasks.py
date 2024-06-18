##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from booking.models import Booking, AbstractScheduledNotification
from celery import shared_task
from django.utils import timezone
from booking.lib import attempt_end_booking

@shared_task
def end_expired_bookings():
    cleanup_set = Booking.objects.filter(end__lte=timezone.now(), ).filter(complete=False)
    for booking in cleanup_set:
        attempt_end_booking(booking)

@shared_task
def send_notifications():
    for notification_types in AbstractScheduledNotification.get_all_unsent_and_ready_notifications():
        for notification in notification_types:
            notification.send()