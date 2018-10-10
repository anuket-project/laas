##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from notifier.models import *
from django.shortcuts import render

def InboxView(request):
    if request.user.is_authenticated:
        user = request.user
    else:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})

    return render(request, "notifier/inbox.html", {'notifier_messages': Notifier.objects.filter(user=user.userprofile)})


def NotificationView(request, notification_id):
    if notification_id == 0:
        pass
    if request.user.is_authenticated:
        user = request.user
    else:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})

    notification = Notifier.objects.get(id=notification_id)
    if not notification.user.user.username == user.username:
        return render(request, "dashboard/login.html", {'title': 'Access Denied'})

    return render(request, "notifier/notification.html", {'notification': notification})
