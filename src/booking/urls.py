##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


"""pharos_dashboard URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url

from booking.views import (
    booking_detail_view,
    BookingDeleteView,
    bookingDelete,
    BookingListView,
    booking_stats_view,
    booking_stats_json
)

app_name = "booking"
urlpatterns = [


    url(r'^detail/(?P<booking_id>[0-9]+)/$', booking_detail_view, name='detail'),
    url(r'^(?P<booking_id>[0-9]+)/$', booking_detail_view, name='booking_detail'),

    url(r'^delete/$', BookingDeleteView.as_view(), name='delete_prefix'),
    url(r'^delete/(?P<booking_id>[0-9]+)/$', BookingDeleteView.as_view(), name='delete'),

    url(r'^delete/(?P<booking_id>[0-9]+)/confirm/$', bookingDelete, name='delete_booking'),

    url(r'^list/$', BookingListView.as_view(), name='list'),
    url(r'^stats/$', booking_stats_view, name='stats'),
    url(r'^stats/json$', booking_stats_json, name='stats_json'),
]
