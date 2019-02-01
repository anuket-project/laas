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
from django.urls import path

from account.views import (
    AccountSettingsView,
    JiraAuthenticatedView,
    JiraLoginView,
    JiraLogoutView,
    UserListView,
    account_resource_view,
    account_booking_view,
    account_images_view,
    account_configuration_view,
    account_detail_view,
    resource_delete_view,
    booking_cancel_view,
    image_delete_view,
    configuration_delete_view
)

app_name = "account"
urlpatterns = [
    url(r'^settings/', AccountSettingsView.as_view(), name='settings'),
    url(r'^authenticated/$', JiraAuthenticatedView.as_view(), name='authenticated'),
    url(r'^login/$', JiraLoginView.as_view(), name='login'),
    url(r'^logout/$', JiraLogoutView.as_view(), name='logout'),
    url(r'^users/$', UserListView.as_view(), name='users'),
    url(r'^my/resources/$', account_resource_view, name="my-resources"),
    path('my/resources/delete/<int:resource_id>', resource_delete_view),
    url(r'^my/bookings/$', account_booking_view, name="my-bookings"),
    path('my/bookings/cancel/<int:booking_id>', booking_cancel_view),
    url(r'^my/images/$', account_images_view, name="my-images"),
    path('my/images/delete/<int:image_id>', image_delete_view),
    url(r'^my/configurations/$', account_configuration_view, name="my-configurations"),
    path('my/configurations/delete/<int:config_id>', configuration_delete_view),
    url(r'^my/$', account_detail_view, name="my-account"),
]
