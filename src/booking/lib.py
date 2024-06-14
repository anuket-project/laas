##############################################################################
# Copyright (c) 2019 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from account.models import UserProfile
import os

from booking.models import Booking
from liblaas.views import booking_end_booking

def get_user_field_opts():
    return {
        'show_from_noentry': False,
        'show_x_results': 5,
        'results_scrollable': True,
        'selectable_limit': -1,
        'placeholder': 'Search for other users',
        'name': 'users',
        'disabled': False
    }


def get_user_items(exclude=None):
    qs = UserProfile.objects.filter(public_user=True).filter(ipa_username__startswith='').select_related('user').exclude(user=exclude)
    items = {}
    for up in qs:
        item = {
            'id': up.id,
            'expanded_name': up.full_name if up.full_name else up.user.username,
            'small_name': up.user.username,
            'string': up.email_addr if up.email_addr else up.user.username,
        }
        items[up.id] = item
    return items

def resolve_hostname(server_address) -> str:
    '''
    Resolves the given host ip from address using the host command.
    Returns string output of "host -st A <server_address>".
    '''
    print(f"trying to resolve {server_address}")
    process = os.popen(f"host -st A {server_address}")
    data = process.read()
    result = process.close()

    if (result is None):
        return data.strip()
    
    return f"Unable to resolve IP for {server_address}"

def attempt_end_booking(booking: Booking) -> tuple[bool, str]:
    """
    Attempts to end the given booking.
    If there is an aggregate id associated with the booking, it will make a request to LibLaaS to end the booking.
    If the request fails or returns an error, the booking will not be marked as complete. Otherwise, it is marked as complete.
    If there is no aggregate id associated with the booking, it is marked as complete.
    Returns True if successfully ended. Otherwise, False.
    """

    if booking is None:
        print("Attempted to end Booking but booking was None!")
        return (False, "Booking not found.")

    if booking.complete:
        print("Attempted to end booking with booking id " + str(booking.id) + ", but was already complete!")
        return (False, "Booking already complete.")

    if not booking.aggregateId:
        print("expiring booking " + str(booking.id) + " has no agg id: ending without hitting LibLaaS")
        booking.complete = True
        booking.save()
    else:
        message = "Unable to end booking"
        print("ending booking " + str(booking.id) + " with agg id: ", booking.aggregateId)
        result: dict = booking_end_booking(booking.aggregateId)
        if result is None:
            print("failed to end booking - no response from LibLaaS!")
        elif result["success"] is True:
            print("ended booking successfully")
            booking.complete = True
            booking.save()
            message = "Success"
        else:
            print("Failed to end booking with reason " + result["details"])
            message = result["details"]

    return (booking.complete, message)