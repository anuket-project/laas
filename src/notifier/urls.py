##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.conf.urls import url

from notifier.views import *

app_name = "notifier"
urlpatterns = [


    url(r'^$', InboxView, name='messages'),
    url(r'^notification/(?P<notification_id>[0-9]+)/$', NotificationView,  name='notifier_single')
]
