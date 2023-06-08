##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from booking.models import Booking
from celery import shared_task
from django.utils import timezone
from api.views import liblaas_end_booking

# todo - make a task to check for expired bookings
@shared_task
def end_expired_bookings():
    print("Celery task for end_expired_bookings() has been triggered")
    cleanup_set = Booking.objects.filter(end__lte=timezone.now(), ).filter(complete=False)
    print("Newly expired bookings: ", cleanup_set)
    for booking in cleanup_set:
        booking.complete = True
        if (booking.aggregateId):
            print("ending booking " + str(booking.id) + " with agg id: ", booking.aggregateId)
            liblaas_end_booking(booking.aggregateId)
        else:
            print("booking " + str(booking.id) + " has no agg id")
        booking.save()
    print("Finished end_expired_bookings()")
