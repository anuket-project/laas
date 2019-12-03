##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.db import models
from account.models import UserProfile
from booking.models import Booking


class Notification(models.Model):
    title = models.CharField(max_length=150)
    content = models.TextField()
    recipients = models.ManyToManyField(UserProfile, related_name='notifications')
    is_html = models.BooleanField(default=True)
    read_by = models.ManyToManyField(UserProfile, related_name='read_notifications')

    def __str__(self):
        return self.title

    def to_preview_html(self):
        return "<h3>" + self.title + "</h3>"  # TODO - template?


class Emailed(models.Model):
    """
    A simple record to remember who has already gotten an email
    to avoid resending
    """
    begin_booking = models.OneToOneField(
        Booking,
        null=True,
        on_delete=models.CASCADE,
        related_name="begin_mail"
    )
    almost_end_booking = models.OneToOneField(
        Booking,
        null=True,
        on_delete=models.CASCADE,
        related_name="warning_mail"
    )
    end_booking = models.OneToOneField(
        Booking,
        null=True,
        on_delete=models.CASCADE,
        related_name="over_mail"
    )

