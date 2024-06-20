##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from abc import abstractmethod
from datetime import timedelta
from account.models import Lab
from django.contrib.auth.models import User
from django.db import models
from typing_extensions import Self
from django.db.models.query import QuerySet
from django.utils import timezone
from liblaas.views import booking_notify_aggregate_expiring
from django.db.models. signals import pre_save, post_save
from django.dispatch import receiver

class Booking(models.Model):
    id = models.AutoField(primary_key=True)
    # All bookings are owned by the user who requested it
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='owner')
    # an owner can add other users to the booking
    collaborators = models.ManyToManyField(User, blank=True, related_name='collaborators')
    # start and end time
    start = models.DateTimeField()
    end = models.DateTimeField()
    reset = models.BooleanField(default=False)
    purpose = models.CharField(max_length=300, blank=False)
    # bookings can be extended without admin approval up to the limit
    ext_days = models.IntegerField(default=42)
    # the hardware that the user has booked
    project = models.CharField(max_length=100, default="", blank=True, null=True)
    lab = models.ForeignKey(Lab, null=True, on_delete=models.SET_NULL)
    pdf = models.TextField(blank=True, default="")
    idf = models.TextField(blank=True, default="")
    # Associated LibLaaS aggregate
    aggregateId = models.CharField(blank=True, max_length=36)

    complete = models.BooleanField(default=False)

    class Meta:
        db_table = 'booking'

    def __str__(self):
        return str(self.purpose) + ' from ' + str(self.start) + ' until ' + str(self.end)

class AbstractScheduledNotification(models.Model):
    """
    Abstract class for defining scheduled notifications.
    Concrete classes should override the _send() method and add any needed fields to the model.
    All models that inherit AbstractScheduledNotification will be queried by the celery task that is responsible for sending notifications.
    """
    class Meta:
        abstract = True

    id = models.AutoField(primary_key=True)
    when = models.DateTimeField(null=False, blank=False)
    sent = models.BooleanField(default=False)

    @staticmethod
    def get_all_unsent_and_ready_notifications() -> list[QuerySet]:
        return [subclass.objects.filter(sent=False, when__lte=timezone.now()) for subclass in AbstractScheduledNotification.__subclasses__()]

    def send(self) -> bool:
        """
        Attempts to send the notification to the proper destination based on notification type. Will not send if already sent.

        DO NOT OVERRIDE THIS METHOD. Concrete implementation should be written into the _send() method.

        If successful, marks as sent.
        Returns True if notification was sent, else False.
        """
        if self.sent:
            print("Notification", self, "already sent!")
            return False
        
        success = self._send()

        if success:
            self.sent = True
            self.save()

        return success

    @abstractmethod
    def _send(self) -> bool:
        """
        Private method containing the implementation for send().
        Override this method in all subclasses.
        This function should only contain the logic required for actually dispatching the notification.

        Checking / updating the "sent" field is handled in the send() method.
        Return 'True' if the notification was sent successfully, else 'False'
        """
        print("Abstract notification can't send!")
        return False
    
class ExpiringBookingNotification(AbstractScheduledNotification):
    for_booking = models.ForeignKey(Booking, null=False, blank=False, on_delete=models.CASCADE)

    def _send(self) -> bool:

        return booking_notify_aggregate_expiring(self.for_booking.aggregateId, self.for_booking.end)

    @staticmethod
    def schedule_expiring_booking_notifications(for_booking: Booking, warning_days: list[int]=[1,3,7]) -> list[Self]:
        """
        Generates expiring notifications for a given booking
        Will not generate notifications for bookings that are shorter than the given warning period (i.e. a booking of length 7 will not generate a 7 day warning notification)

        Args:
            for_booking - Booking object to link to Notification\n
            warning_days - List of days before booking end to send warning notification

        Example Usage:
            ExpiringBookingNotification.generate_expiring_booking_notifications(Booking.objects.get(id=123), [1,3,7])
        """
        newly_created: list[ExpiringBookingNotification] = []
        booking_remaining_days: int = (for_booking.end - timezone.now()).days
        for day in warning_days:
            if day < booking_remaining_days:
                newly_created.append(ExpiringBookingNotification.objects.create(for_booking=for_booking, when=(for_booking.end - timedelta(day))))

        return newly_created


@receiver(pre_save, sender=Booking)
def on_booking_save_update_notifications(sender, instance, **kwargs):
    """
    When an existing booking is updated and the end date is changed, mark all existing ExpiringBookingNotifications as read and schedule new ones.

    NOTE - Updating objects using the admin site does not use the save() method! Triggers will not activate.
    """
    if instance.id is None:
        # This is a new booking: so just NOOP
        return

    previous = Booking.objects.get(id=instance.id)
    if previous.end != instance.end:
        existing_notifs = ExpiringBookingNotification.objects.filter(for_booking=instance)
        for en in existing_notifs:
            en.sent = True
            en.save()

        ExpiringBookingNotification.schedule_expiring_booking_notifications(for_booking=instance)

@receiver(post_save, sender=Booking)
def on_booking_creation_schedule_notifications(sender, instance, created, **kwargs):
    """
    Creates scheduled notifications when a booking is created

    NOTE - Creating an object using the admin site WILL call save() (unlike updating) and create notifications
    """
    if created:
        ExpiringBookingNotification.schedule_expiring_booking_notifications(instance)