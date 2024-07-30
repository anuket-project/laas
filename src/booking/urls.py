##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


"""
laas_dashboard URL Configuration.

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
from django.urls import path

from booking.views import (
    booking_detail_view,
    BookingDeleteView,
    bookingDelete,
    BookingListView,
    get_host_ip,
    manage_collaborators,
    extend_booking,
    request_extend_booking
)

app_name = 'booking'
urlpatterns = [
    path('detail/<int:booking_id>/', booking_detail_view, name='detail'),
    path('<int:booking_id>/', booking_detail_view, name='booking_detail'),
    path('delete/', BookingDeleteView.as_view(), name='delete_prefix'),
    path('delete/<int:booking_id>/', BookingDeleteView.as_view(), name='delete'),
    path('delete/<int:booking_id>/confirm/', bookingDelete, name='delete_booking'),
    path('list/', BookingListView.as_view(), name='list'),
    path('resolve/', get_host_ip, name='get_host_ip'),
    path('collaborators/<int:booking_id>/', manage_collaborators, name='collaborators'),
    path('extend/<int:booking_id>/', extend_booking, name='extend'),
    path('request-extend/<int:booking_id>/', request_extend_booking, name='extend')

]
