##############################################################################
# Copyright (c) 2020 Parker Berberian, Sawyer Bergeron, Sean Smith and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
import os
from booking.models import Booking
from resource_inventory.models import ResourceQuery, ResourceProfile
from datetime import datetime, timedelta
from collections import Counter
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

        anuket_colors = [
            '#6BDAD5',  # Turquoise
            '#E36386',  # Pale Violet Red
            '#F5B335',  # Sandy Brown
            '#007473',  # Teal
            '#BCE194',  # Gainsboro
            '#00CE7C',  # Sea Green
        ]

        lfedge_colors = [
            '#0049B0',
            '#B481A5',
            '#6CAFE4',
            '#D33668',
            '#28245A'
        ]

        x = []
        y = []
        users = []
        projects = []
        profiles = {str(profile): [] for profile in ResourceProfile.objects.all()}

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

            x.append(str(start.month) + '-' + str(start.day))
            y.append(books.count())

            step_profiles = Counter([
                str(config.profile)
                for book in books
                for config in book.resource.template.getConfigs()
            ])

            for profile in ResourceProfile.objects.all():
                profiles[str(profile)].append(step_profiles[str(profile)])
            users.append(active_users)

            start += timedelta(hours=12)

        in_use = len(ResourceQuery.filter(working=True, booked=True))
        not_in_use = len(ResourceQuery.filter(working=True, booked=False))
        maintenance = len(ResourceQuery.filter(working=False))

        projects = [x.project for x in bookings]
        proj_count = sorted(Counter(projects).items(), key=lambda x: x[1])

        project_keys = [proj[0] for proj in proj_count[-5:]]
        project_keys = ['None' if x is None else x for x in project_keys]
        project_counts = [proj[1] for proj in proj_count[-5:]]

        resources = {key: [x, value] for key, value in profiles.items()}

        return {
            "resources": resources,
            "booking": [x, y],
            "user": [x, users],
            "utils": [in_use, not_in_use, maintenance],
            "projects": [project_keys, project_counts],
            "colors": anuket_colors if os.environ.get('TEMPLATE_OVERRIDE_DIR') == 'laas' else lfedge_colors
        }
