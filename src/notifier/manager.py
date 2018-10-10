##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from booking.models import *
from notifier.models import Notifier, MetaBooking, LabMessage
from django.utils import timezone
from datetime import timedelta
from django.template import Template, Context
from account.models import UserProfile

from django.db import models

class NotifyPeriodic(object):
    def task():
        bookings_new = Booking.objects.filter(metabooking__isnull=True)
        bookings_old = Booking.objects.filter(end__lte=timezone.now() + timedelta(hours=24)).filter(metabooking__ended_notified=False)

        for booking in bookings_old:
            metabooking = booking.metabooking
            if booking.end <= timezone.now() + timedelta(hours=24):
                if not metabooking.ending_notified:
                    Notify().notify(Notify.TOCLEAN, booking)
                    metabooking.ending_notified = True
                    metabooking.save()
            if booking.end <= timezone.now():
                metabooking = booking.metabooking
                if not metabooking.ended_notified:
                    Notify().notify(Notify.CLEANED, booking)
                    metabooking.ended_notified = True
                    metabooking.save()

        for booking in bookings_new:
            metabooking = MetaBooking()
            metabooking.booking = booking
            metabooking.created_notified = True
            metabooking.save()

            Notify().notify(Notify.CREATED, booking)


class Notify(object):

    CREATED = "created"
    TOCLEAN = "toclean"
    CLEANED = "cleaned"

    TITLES = {}
    TITLES["created"] = "Your booking has been confirmed"
    TITLES["toclean"] = "Your booking is ending soon"
    TITLES["cleaned"] = "Your booking has ended"

    """
    Lab message is provided with the following context elements:
    * if is for owner or for collaborator (if owner)
    * recipient username (<owner, collaborator>.username)
    * recipient full name (<owner, collaborator>.userprofile.full_name)
    * booking it pertains to (booking)
    * status message should convey (currently "created", "toclean" and "cleaned" as strings)
    It should be a django template that can be rendered with these context elements
    and should generally use all of them in one way or another.
    It should be applicable to email, the web based general view, and should be scalable for
    all device formats across those mediums.
    """
    def notify(self, notifier_type, booking):
        template = Template(LabMessage.objects.filter(lab=booking.lab).first().msg)

        context = {}
        context["owner"] = booking.owner
        context["notify_type"] = notifier_type
        context["booking"] = booking
        message = template.render(Context(context))
        notifier = Notifier()
        notifier.title = self.TITLES[notifier_type]
        notifier.content = message
        notifier.user = booking.owner.userprofile
        notifier.sender = str(booking.lab)
        notifier.save()
        notifier.send()


        context["owner"] = False

        for user in booking.collaborators.all():
            context["collaborator"] = user
            message = template.render(Context(context))
            notifier = Notifier()
            notifier.title = self.TITLES[notifier_type]
            notifier.content = message
            notifier.user = UserProfile.objects.get(user=user)
            notifier.sender = str(booking.lab)
            notifier.save()
            notifier.send()
