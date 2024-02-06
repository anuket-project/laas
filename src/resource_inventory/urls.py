##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.conf.urls import url
from django.urls import path

from resource_inventory.views import host_list_view, profile_view
app_name = 'resource'
urlpatterns = [
    url(r'^list/$', host_list_view, name='host-list'),
    path('profile/<str:resource_id>', profile_view),
]