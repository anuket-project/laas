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
        data = []
        x = []
        y = []
        users = []
        now = datetime.datetime.now(pytz.utc)
        delta = datetime.timedelta(days=span)
        end = now - delta
        bookings = Booking.objects.filter(start__lte=now, end__gte=end)
        for booking in bookings:  # collect data from each booking
            user_list = [u.pk for u in booking.collaborators.all()]
            user_list.append(booking.owner.pk)
            data.append((booking.start, 1, user_list))
            data.append((booking.end, -1, user_list))

        # sort based on time
        data.sort(key=lambda i: i[0])

        # collect data
        count = 0
        active_users = {}
        for datum in data:
            x.append(str(datum[0]))  # time
            count += datum[1]  # booking count
            y.append(count)
            for pk in datum[2]:  # maintain count of each user's active bookings
                active_users[pk] = active_users.setdefault(pk, 0) + datum[1]
                if active_users[pk] == 0:
                    del active_users[pk]
            users.append(len([x for x in active_users.values() if x > 0]))

        return {"booking": [x, y], "user": [x, users]}
