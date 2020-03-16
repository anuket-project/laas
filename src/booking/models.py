##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from resource_inventory.models import ResourceBundle, OPNFVConfig
from account.models import Lab
from django.contrib.auth.models import User
from django.db import models
import resource_inventory.resource_manager


class Booking(models.Model):
    id = models.AutoField(primary_key=True)
    # All bookings are owned by the user who requested it
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='owner')
    # an owner can add other users to the booking
    collaborators = models.ManyToManyField(User, related_name='collaborators')
    # start and end time
    start = models.DateTimeField()
    end = models.DateTimeField()
    reset = models.BooleanField(default=False)
    jira_issue_id = models.IntegerField(null=True, blank=True)
    jira_issue_status = models.CharField(max_length=50, blank=True)
    purpose = models.CharField(max_length=300, blank=False)
    # bookings can be extended a limited number of times
    ext_count = models.IntegerField(default=2)
    # the hardware that the user has booked
    resource = models.ForeignKey(ResourceBundle, on_delete=models.SET_NULL, null=True)
    opnfv_config = models.ForeignKey(OPNFVConfig, on_delete=models.SET_NULL, null=True)
    project = models.CharField(max_length=100, default="", blank=True, null=True)
    lab = models.ForeignKey(Lab, null=True, on_delete=models.SET_NULL)
    pdf = models.TextField(blank=True, default="")
    idf = models.TextField(blank=True, default="")

    class Meta:
        db_table = 'booking'

    def save(self, *args, **kwargs):
        """
        Save the booking if self.user is authorized and there is no overlapping booking.

        Raise PermissionError if the user is not authorized
        Raise ValueError if there is an overlapping booking
        """
        if self.start >= self.end:
            raise ValueError('Start date is after end date')
        # conflicts end after booking starts, and start before booking ends
        conflicting_dates = Booking.objects.filter(resource=self.resource).exclude(id=self.id)
        conflicting_dates = conflicting_dates.filter(end__gt=self.start)
        conflicting_dates = conflicting_dates.filter(start__lt=self.end)
        if conflicting_dates.count() > 0:
            raise ValueError('This booking overlaps with another booking')
        return super(Booking, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        res = self.resource
        self.resource = None
        self.save()
        resource_inventory.resource_manager.ResourceManager.getInstance().deleteResourceBundle(res)
        return super(self.__class__, self).delete(*args, **kwargs)

    def __str__(self):
        return str(self.purpose) + ' from ' + str(self.start) + ' until ' + str(self.end)
