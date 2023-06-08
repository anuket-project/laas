##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.conf.urls import url
from workflow.views import design_a_pod_view, book_a_pod_view

app_name = 'workflow'
urlpatterns = [
    url(r'^design/$', design_a_pod_view, name='design_a_pod'),
    url(r'^book/$', book_a_pod_view, name='book_a_pod'),
]
