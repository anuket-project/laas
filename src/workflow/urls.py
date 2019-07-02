##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.conf.urls import url
from django.conf import settings

from workflow.views import delete_session, manager_view, viewport_view, add_workflow, cancel_workflow
from workflow.models import Repository
from workflow.resource_bundle_workflow import Define_Hardware, Define_Nets, Resource_Meta_Info
from workflow.booking_workflow import SWConfig_Select, Booking_Resource_Select, Booking_Meta

app_name = 'workflow'
urlpatterns = [

    url(r'^finish/$', delete_session, name='delete_session'),
    url(r'^manager/$', manager_view, name='manager'),
    url(r'^add/$', add_workflow, name='add_workflow'),
    url(r'^cancel/$', cancel_workflow, name='cancel_workflow'),
    url(r'^$', viewport_view, name='viewport')
]

if settings.TESTING:
    urlpatterns.append(url(r'^workflow/step/define_hardware$', Define_Hardware("", Repository()).test_render))
    urlpatterns.append(url(r'^workflow/step/define_net$', Define_Nets("", Repository()).test_render))
    urlpatterns.append(url(r'^workflow/step/resource_meta$', Resource_Meta_Info("", Repository()).test_render))
    urlpatterns.append(url(r'^workflow/step/booking_meta$', Booking_Meta("", Repository()).test_render))
    urlpatterns.append(url(r'^workflow/step/software_select$', SWConfig_Select("", Repository()).test_render))
    urlpatterns.append(url(r'^workflow/step/resource_select$', Booking_Resource_Select("", Repository()).test_render))
