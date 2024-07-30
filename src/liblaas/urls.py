##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.urls import path, re_path

from liblaas.endpoints import *

app_name = 'liblaas'
urlpatterns = [
    re_path(r'^flavor/(?P<lab_name>[A-Za-z]+)$', request_list_flavors, name='flavor'),
    re_path(r'^template/(?P<lab_name>[A-Za-z]+)$', request_list_template, name='template'),
    path('template/create/', request_create_template, name='template_create'),
    path('booking/create/', request_create_booking, name='booking_create'),
    path('migrate/new/', request_migrate_new, name='migrate_new'),
    path('migrate/conflict/', request_migrate_conflict, name='migrate_conflict'),
    path('ipa/ssh/', request_set_ssh, name='set_ssh'),
    path('ipa/company/', request_set_company, name='set_company'),
    re_path(r'^ipmi/set/(?P<host_id>[A-Za-z0-9_-]+)$', request_ipmi_setpower, name='ipmi_set'),
    re_path(r'^ipmi/get/(?P<host_id>[A-Za-z0-9_-]+)$', request_ipmi_getpower, name='ipmi_get'),
    re_path(r'^reimage/(?P<host_id>[A-Za-z0-9_-]+)$', request_image_set, name='image_set'),
]