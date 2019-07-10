##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.conf.urls import url

from workflow.views import manager_view, viewport_view, add_workflow, remove_workflow, create_workflow

app_name = 'workflow'
urlpatterns = [

    url(r'^manager/$', manager_view, name='manager'),
    url(r'^add/$', add_workflow, name='add_workflow'),
    url(r'^create/$', create_workflow, name='create_workflow'),
    url(r'^pop/$', remove_workflow, name='remove_workflow'),
    url(r'^$', viewport_view, name='viewport')
]
