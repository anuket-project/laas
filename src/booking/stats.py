##############################################################################
# Copyright (c) 2020 Parker Berberian, Sawyer Bergeron, Sean Smith and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
from booking.models import Booking
from datetime import datetime, timedelta
import pytz


class StatisticsManager(object):

    @staticmethod
    def getContinuousBookingTimeSeries(span=28):
        """
        Calculate Booking usage data points.

        Gathers all active bookings that fall in interval [(now - span), (now + 1 week)].
        x data points are every 12 hours
        y values are the integer number of bookings/users active at time
        """

        x = []
        y = []
        users = []

        now = datetime.now(pytz.utc)
        delta = timedelta(days=span)
        start = now - delta
        end = now + timedelta(weeks=1)

        bookings = Booking.objects.filter(
            start__lte=end,
            end__gte=start
        ).prefetch_related("collaborators")

        # get data
        while start <= end:
            active_users = 0

            books = bookings.filter(
                start__lte=start,
                end__gte=start
            ).prefetch_related("collaborators")

            for booking in books:
                active_users += booking.collaborators.all().count() + 1

            x.append(str(start))
            y.append(books.count())
            users.append(active_users)

            start += timedelta(hours=12)

        return {"booking": [x, y], "user": [x, users]}
