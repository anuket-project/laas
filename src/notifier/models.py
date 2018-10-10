##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.db import models
from booking.models import Booking
from account.models import UserProfile
from fernet_fields import EncryptedTextField
from account.models import Lab


class MetaBooking(models.Model):
    id = models.AutoField(primary_key=True)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="metabooking")
    ending_notified = models.BooleanField(default=False)
    ended_notified = models.BooleanField(default=False)
    created_notified = models.BooleanField(default=False)


class LabMessage(models.Model):
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE)
    msg = models.TextField()  # django template should be put here


class Notifier(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=240)
    content = EncryptedTextField()
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    sender = models.CharField(max_length=240, default='unknown')
    message_type = models.CharField(max_length=240, default='email', choices=(
        ('email', 'Email'),
        ('webnotification', 'Web Notification')))
    msg_sent = ''

    def __str__(self):
        return self.title

    """
    Implement for next PR: send Notifier by media agreed to by user
    """
    def send(self):
        pass

    def getEmail(self):
        return self.user.email_addr
