#############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, Sean Smith, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
import pytz
from datetime import timedelta, datetime

from django.test import TestCase

from booking.models import Booking
from booking.stats import StatisticsManager as sm
from dashboard.testing_utils import make_user


class StatsTestCases(TestCase):

    def test_no_booking_outside_span(self):
        now = datetime.now(pytz.utc)

        bad_date = now + timedelta(days=1200)
        Booking.objects.create(start=now, end=bad_date, owner=make_user(username='jj'))

        actual = sm.getContinuousBookingTimeSeries()
        dates = actual['booking'][0]

        for date in dates:
            self.assertNotEqual(date, bad_date)

    def check_booking_and_user_counts(self):
        now = datetime.now(pytz.utc)

        for i in range(20):
            Booking.objects.create(
                start=now,
                end=now + timedelta(weeks=3),
                owner=make_user(username='a'))

        for i in range(30):
            Booking.objects.create(
                start=now + timedelta(days=5),
                end=now + timedelta(weeks=3, days=5),
                owner=make_user(username='a'))

        for i in range(120):
            Booking.objects.create(
                start=now + timedelta(weeks=1),
                end=now + timedelta(weeks=4),
                owner=make_user(username='a'))

        dates = [[now, 20], [now + timedelta(days=5), 30], [now + timedelta(weeks=1), 120]]
        actual = sm.getContinuousBookingTimeSeries()

        for date in dates:
            self.assertEqual(date[1], actual['booking'][date[0]])
            self.assertEqual(date[1], actual['booking'][date[1]])
