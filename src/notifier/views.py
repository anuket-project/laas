##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from notifier.models import Notification
from django.shortcuts import render


def InboxView(request):
    if request.user.is_authenticated:
        user = request.user
    else:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})

    return render(request, "notifier/inbox.html", {'notifications': Notification.objects.filter(recipients=user.userprofile)})


def NotificationView(request, notification_id):
    if request.user.is_authenticated:
        user = request.user
    else:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})

    notification = Notification.objects.get(id=notification_id)
    if user.userprofile not in notification.recipients.all():
        return render(request, "dashboard/login.html", {'title': 'Access Denied'})

    return render(request, "notifier/notification.html", {'notification': notification})
