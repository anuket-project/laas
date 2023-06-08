##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from account.models import Lab
from django.contrib.auth.models import User
from django.db import models
from django.core.validators import RegexValidator


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
    # bookings can be extended a limited number of times
    ext_count = models.IntegerField(default=2)
    # the hardware that the user has booked
    project = models.CharField(max_length=100, default="", blank=True, null=True)
    lab = models.ForeignKey(Lab, null=True, on_delete=models.SET_NULL)
    pdf = models.TextField(blank=True, default="")
    idf = models.TextField(blank=True, default="")
    # Associated LibLaaS aggregate
    aggregateId = models.CharField(blank=True, max_length=36, validators=[RegexValidator(regex='^[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$', message='aggregate_id must be a valid UUID', code='nomatch')])

    complete = models.BooleanField(default=False)

    class Meta:
        db_table = 'booking'

    def __str__(self):
        return str(self.purpose) + ' from ' + str(self.start) + ' until ' + str(self.end)
