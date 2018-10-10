##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.test import TestCase
from notifier.models import *
from django.contrib.auth.models import User

class NotifierTestCase(TestCase):

    def test_valid_notifier_saves(self):

        sender = User.objects.create()
        recipient = User.objects.create()
        self.assertTrue(
            Notifier.objects.create(
                title='notification title',
                content='notification body',
                user=recipient,
                sender=sender,
                message_type='email'
            )
        )
