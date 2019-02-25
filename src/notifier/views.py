##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.shortcuts import render
from notifier.models import Notification
from django.db.models import Q


def InboxView(request):
    if request.user.is_authenticated:
        user = request.user
    else:
        return render(request, "dashboard/login.html",
                      {'title': 'Authentication Required'})

    return render(request,
                  "notifier/inbox.html",
                  {'unread_notifications': Notification.objects.filter(recipients=user.userprofile).order_by('-id').filter(~Q(read_by=user.userprofile)),
                      'read_notifications': Notification.objects.filter(recipients=user.userprofile).order_by('-id').filter(read_by=user.userprofile)})


def NotificationView(request, notification_id):

    if request.user.is_authenticated:
        user = request.user
    else:
        return render(request,
                      "dashboard/login.html",
                      {'title': 'Authentication Required'})

    notification = Notification.objects.get(id=notification_id)
    if user.userprofile not in notification.recipients.all():
        return render(request,
                      "dashboard/login.html", {'title': 'Access Denied'})

    notification.read_by.add(user.userprofile)
    notification.save()
    if request.method == 'POST':
        if 'delete' in request.POST:
            # handle deleting
            notification.recipients.remove(user.userprofile)
            if not notification.recipients.exists():
                notification.delete()
            else:
                notification.save()

        if 'unread' in request.POST:
            notification.read_by.remove(user.userprofile)
            notification.save()

    return render(request,
                  "notifier/notification.html", {'notification': notification})
