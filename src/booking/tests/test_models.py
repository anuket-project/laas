##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from datetime import timedelta

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.utils import timezone

# from booking.models import *
from booking.models import Booking
from resource_inventory.models import ResourceBundle, GenericResourceBundle, ConfigBundle


class BookingModelTestCase(TestCase):

    count = 0

    def setUp(self):
        self.owner = User.objects.create(username='owner')

        self.res1 = ResourceBundle.objects.create(
            template=GenericResourceBundle.objects.create(
                name="gbundle" + str(self.count)
            )
        )
        self.count += 1
        self.res2 = ResourceBundle.objects.create(
            template=GenericResourceBundle.objects.create(
                name="gbundle2" + str(self.count)
            )
        )
        self.count += 1
        self.user1 = User.objects.create(username='user1')

        self.add_booking_perm = Permission.objects.get(codename='add_booking')
        self.user1.user_permissions.add(self.add_booking_perm)

        self.user1 = User.objects.get(pk=self.user1.id)
        self.config_bundle = ConfigBundle.objects.create(
            owner=self.user1,
            name="test config"
        )

    def test_start_end(self):
        """
        if the start of a booking is greater or equal then the end,
        saving should raise a ValueException
        """
        start = timezone.now()
        end = start - timedelta(weeks=1)
        self.assertRaises(
            ValueError,
            Booking.objects.create,
            start=start,
            end=end,
            resource=self.res1,
            owner=self.user1,
            config_bundle=self.config_bundle
        )
        end = start
        self.assertRaises(
            ValueError,
            Booking.objects.create,
            start=start,
            end=end,
            resource=self.res1,
            owner=self.user1,
            config_bundle=self.config_bundle
        )

    def test_conflicts(self):
        """
        saving an overlapping booking on the same resource
        should raise a ValueException
        saving for different resources should succeed
        """
        start = timezone.now()
        end = start + timedelta(weeks=1)
        self.assertTrue(
            Booking.objects.create(
                start=start,
                end=end,
                owner=self.user1,
                resource=self.res1,
                config_bundle=self.config_bundle
            )
        )

        self.assertRaises(
            ValueError,
            Booking.objects.create,
            start=start,
            end=end,
            resource=self.res1,
            owner=self.user1,
            config_bundle=self.config_bundle
        )

        self.assertRaises(
            ValueError,
            Booking.objects.create,
            start=start + timedelta(days=1),
            end=end - timedelta(days=1),
            resource=self.res1,
            owner=self.user1,
            config_bundle=self.config_bundle
        )

        self.assertRaises(
            ValueError,
            Booking.objects.create,
            start=start - timedelta(days=1),
            end=end,
            resource=self.res1,
            owner=self.user1,
            config_bundle=self.config_bundle
        )

        self.assertRaises(
            ValueError,
            Booking.objects.create,
            start=start - timedelta(days=1),
            end=end - timedelta(days=1),
            resource=self.res1,
            owner=self.user1,
            config_bundle=self.config_bundle
        )

        self.assertRaises(
            ValueError,
            Booking.objects.create,
            start=start,
            end=end + timedelta(days=1),
            resource=self.res1,
            owner=self.user1,
            config_bundle=self.config_bundle
        )

        self.assertRaises(
            ValueError,
            Booking.objects.create,
            start=start + timedelta(days=1),
            end=end + timedelta(days=1),
            resource=self.res1,
            owner=self.user1,
            config_bundle=self.config_bundle
        )

        self.assertTrue(
            Booking.objects.create(
                start=start - timedelta(days=1),
                end=start,
                owner=self.user1,
                resource=self.res1,
                config_bundle=self.config_bundle
            )
        )

        self.assertTrue(
            Booking.objects.create(
                start=end,
                end=end + timedelta(days=1),
                owner=self.user1,
                resource=self.res1,
                config_bundle=self.config_bundle
            )
        )

        self.assertTrue(
            Booking.objects.create(
                start=start - timedelta(days=2),
                end=start - timedelta(days=1),
                owner=self.user1,
                resource=self.res1,
                config_bundle=self.config_bundle
            )
        )

        self.assertTrue(
            Booking.objects.create(
                start=end + timedelta(days=1),
                end=end + timedelta(days=2),
                owner=self.user1,
                resource=self.res1,
                config_bundle=self.config_bundle
            )
        )

        self.assertTrue(
            Booking.objects.create(
                start=start,
                end=end,
                owner=self.user1,
                resource=self.res2,
                config_bundle=self.config_bundle
            )
        )

    def test_extensions(self):
        """
        saving a booking with an extended end time is allows to happen twice,
        and each extension must be a maximum of one week long
        """
        start = timezone.now()
        end = start + timedelta(weeks=1)
        self.assertTrue(
            Booking.objects.create(
                start=start,
                end=end,
                owner=self.user1,
                resource=self.res1,
                config_bundle=self.config_bundle
            )
        )

        booking = Booking.objects.all().first()  # should be only thing in db

        self.assertEquals(booking.ext_count, 2)
        booking.end = booking.end + timedelta(days=3)
        try:
            booking.save()
        except Exception:
            self.fail("save() threw an exception")
