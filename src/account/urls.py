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
from django.urls import path, re_path

from account.views import (
    OIDCLoginView,
    LogoutView,
    account_resource_view,
    account_booking_view,
    account_detail_view,
    account_settings_view,
    account_dev_login_view
)

app_name = 'account'

urlpatterns = [
    path('settings/', account_settings_view, name='settings'),
    path('login/', OIDCLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('my/resources/', account_resource_view, name='my-resources'),
    path('my/bookings/', account_booking_view, name='my-bookings'),
    path('my/', account_detail_view, name='my-account'),
    path('dev_login/', account_dev_login_view, name='dev-login'),
]
