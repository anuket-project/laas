##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.conf.urls import url

from liblaas.endpoints import *

app_name = 'liblaas'
urlpatterns = [
    url(r'^flavor/(?P<lab_name>[A-Za-z]+)$', request_list_flavors, name='flavor'),
    url(r'^template/(?P<lab_name>[A-Za-z]+)$', request_list_template, name='template'),
    url(r'^template/create/$', request_create_template, name='template_create'),
    url(r'^booking/create/$', request_create_booking, name='booking_create'),
    url(r'^migrate/new/$', request_migrate_new, name='migrate_new'),
    url(r'^migrate/conflict/$', request_migrate_conflict, name='migrate_conflict'),
    url(r'^ipa/ssh/$', request_set_ssh, name='set_ssh'),
    url(r'^ipa/company/$', request_set_company, name='set_company'),
    url(r'^ipmi/set/(?P<host_id>[A-Za-z0-9_-]+)$', request_ipmi_setpower, name='ipmi_set'),
    url(r'^ipmi/get/(?P<host_id>[A-Za-z0-9_-]+)$', request_ipmi_getpower, name='ipmi_get'),
]