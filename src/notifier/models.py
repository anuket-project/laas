##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.db import models
from jira import JIRA, JIRAError
from dashboard.models import Resource
from booking.models import Booking
from django.contrib.auth.models import User
from account.models import UserProfile
from django.contrib import messages
from django.db.models.signals import pre_save
from fernet_fields import EncryptedTextField

class Notifier(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=240)
    content = EncryptedTextField()
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    sender = models.CharField(max_length=240, default='unknown')
    message_type = models.CharField(max_length=240, default='email', choices=(
        ('email','Email'), 
        ('webnotification', 'Web Notification')))
    msg_sent = ''

    import notifier.dispatchers

    def __str__(self):
        return self.title

    def getEmail(self):
        return self.user.email_addr

