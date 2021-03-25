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
from django.conf import settings
from booking.models import Booking
from notifier.models import Emailed, Email
from notifier.manager import NotificationHandler
from django.core.mail import send_mail

import os


@shared_task
def notify_expiring():
    """Notify users if their booking is within 48 hours of expiring."""
    expire_time = timezone.now() + timezone.timedelta(hours=settings.EXPIRE_HOURS)
    # Don't email people about bookings that have started recently
    start_time = timezone.now() - timezone.timedelta(hours=settings.EXPIRE_LIFETIME)
    bookings = Booking.objects.filter(
        end__lte=expire_time,
        end__gte=timezone.now(),
        start__lte=start_time
    )
    for booking in bookings:
        if Emailed.objects.filter(almost_end_booking=booking).exists():
            continue
        NotificationHandler.notify_booking_expiring(booking)
        Emailed.objects.create(almost_end_booking=booking)


@shared_task
def dispatch_emails():
    for email in Email.objects.filter(sent=False):
        email.sent = True
        email.save()
        send_mail(
            email.title,
            email.message,
            os.environ.get("DEFAULT_FROM_EMAIL", "opnfv@laas-dashboard"),
            [email.recipient],
            fail_silently=False)
