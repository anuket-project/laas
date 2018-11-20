##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
from booking.models import Booking
import datetime
import pytz


class StatisticsManager(object):

    @staticmethod
    def getContinuousBookingTimeSeries(span=28):
        """
        Will return a dictionary of names and 2-D array of x and y data points.
        e.g. {"plot1": [["x1", "x2", "x3"],["y1", "y2", "y3]]}
        x values will be dates in string
        every change (booking start / end) will be reflected,
        instead of one data point per day
        y values are the integer number of bookings/users active at
        some point in the given date span is the number of days to plot.
        The last x value will always be the current time
        """
        x_set = set()
        x = []
        y = []
        users = []
        now = datetime.datetime.now(pytz.utc)
        delta = datetime.timedelta(days=span)
        end = now - delta
        bookings = Booking.objects.filter(start__lte=now, end__gte=end)
        for booking in bookings:
            x_set.add(booking.start)
            if booking.end < now:
                x_set.add(booking.end)

        x_set.add(now)
        x_set.add(end)

        x_list = list(x_set)
        x_list.sort(reverse=True)
        for time in x_list:
            x.append(str(time))
            active = Booking.objects.filter(start__lte=time, end__gt=time)
            booking_count = len(active)
            users_set = set()
            for booking in active:
                users_set.add(booking.owner)
                for user in booking.collaborators.all():
                    users_set.add(user)
            y.append(booking_count)
            users.append(len(users_set))

        return {"booking": [x, y], "user": [x, users]}
