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
from types import FunctionType
from dashboard.utils import send_email
from laas_dashboard.settings import (
    SITE_CONTACT,
)


def email_if_error(append_head: str, prepend_body: str) -> FunctionType:
    """
    Should be used as a decorator
    Emails the value of the error (ie the error message) to the set SITE_CONTACT in settings
    """
    def inner_decorator(function: FunctionType):
        def wrapper():
            try: 
                function()
            except Exception as error:
                print(f"Error happened: '{str(error)}'. Sending notification email")
                send_email(subject=f"Dashboard encountered error in function {function.__name__}: {append_head}", message=f"{prepend_body}\n{str(error)}", recipient_list=[SITE_CONTACT])

        return wrapper
    return inner_decorator


@email_if_error("Celery error", "Unable to end booking, it appears the backend is down.")
@shared_task
def end_expired_bookings():
    cleanup_set = Booking.objects.filter(end__lte=timezone.now(), ).filter(complete=False)
    for booking in cleanup_set:
        attempt_end_booking(booking)

@email_if_error("Celery error", "Unable to send notification email:")
@shared_task
def send_notifications():
    for notification_types in AbstractScheduledNotification.get_all_unsent_and_ready_notifications():
        for notification in notification_types:
            if (not notification.send()):
                raise RuntimeError(f"Failed to send notification for {notification}")

