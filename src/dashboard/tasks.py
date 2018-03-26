##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from django.conf import settings
from booking.models import Booking

from jenkins.models import JenkinsStatistic

@shared_task
def database_cleanup():
    now = timezone.now()
    JenkinsStatistic.objects.filter(timestamp__lt=now - timedelta(weeks=4)).delete()

def booking_cleanup():
    expire_time = timedelta(days=int(settings.BOOKING_EXP_TIME))
    expire_number = int(settings.BOOKING_MAX_NUM)
    expired_set = Booking.objects.filter(end__lte=timezone.now())
    expired_count = len(expired_set)

    for booking in expired_set:
        if timezone.now() - booking.end > expire_time:
            booking.delete()
            expired_count = expired_count - 1

    if expired_count > expire_number:
        oldest = expired_set.order_by("end")[:expired_count-expire_number]
        for booking in oldest:
            booking.delete()
