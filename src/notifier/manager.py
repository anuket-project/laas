##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron and others.
# Copyright (c) 2020 Sawyer Bergeron, Sean Smith, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
import os
from notifier.models import Notification, Emailed, Email

from django.template.loader import render_to_string
from django.utils import timezone


class NotificationHandler(object):

    @classmethod
    def notify_new_booking(cls, booking):
        template = "notifier/new_booking.html"
        titles = ["You have a new booking (" + str(booking.id) + ")", "You have been added to a booking (" + str(booking.id) + ")"]
        cls.booking_notify(booking, template, titles)

    @classmethod
    def notify_booking_end(cls, booking):
        template = "notifier/end_booking.html"
        titles = ["Your booking (" + str(booking.id) + ") has ended", "A booking (" + str(booking.id) + ") that you collaborate on has ended"]
        cls.booking_notify(booking, template, titles)

    @classmethod
    def notify_booking_expiring(cls, booking):
        template = "notifier/expiring_booking.html"
        titles = ["Your booking (" + str(booking.id) + ") is about to expire", "A booking (" + str(booking.id) + ") that you collaborate on is about to expire"]
        cls.booking_notify(booking, template, titles)
        cls.email_booking_expiring(booking)

    @classmethod
    def booking_notify(cls, booking, template, titles):
        """
        Create a notification for a booking owner and collaborators using the template.

        titles is a list - the first is the title for the owner's notification,
            the last is the title for the collaborators'
        """
        owner_notif = Notification.objects.create(
            title=titles[0],
            content=render_to_string(
                template,
                context={
                    "booking": booking,
                    "owner": True
                }
            )
        )
        owner_notif.recipients.add(booking.owner.userprofile)
        if not booking.collaborators.all().exists():
            return  # no collaborators - were done

        collab_notif = Notification.objects.create(
            title=titles[-1],
            content=render_to_string(
                template,
                context={
                    "booking": booking,
                    "owner": False
                }
            )
        )
        for c in booking.collaborators.all():
            collab_notif.recipients.add(c.userprofile)

    @classmethod
    def email_job_fulfilled(cls, job):
        template_name = "notifier/email_fulfilled.txt"
        all_tasks = job.get_tasklist()
        users = list(job.booking.collaborators.all())
        users.append(job.booking.owner)
        for user in users:
            user_tasklist = []
            # gather up all the relevant messages from the lab
            for task in all_tasks:
                if (not hasattr(task.config, "user")) or task.config.user == user:
                    user_tasklist.append(
                        {
                            "title": task.type_str() + " Message: ",
                            "content": task.message
                        }
                    )
            # gather up all the other needed info
            context = {
                "owner": user == job.booking.owner,
                "user_name": user.userprofile.full_name,
                "messages": user_tasklist,
                "booking_url": os.environ.get("DASHBOARD_URL", "<Dashboard url>") + "/booking/detail/" + str(job.booking.id) + "/"
            }

            # render email template
            message = render_to_string(template_name, context)

            # finally, queue email for sending
            Email.objects.create(title="Your Booking is Ready", message=message, recipient=user.userprofile.email_addr)

    @classmethod
    def email_booking_over(cls, booking):
        template_name = "notifier/email_ended.txt"
        hostnames = [host.name for host in booking.resource.get_resources()]
        users = list(booking.collaborators.all())
        users.append(booking.owner)
        for user in users:
            context = {
                "user_name": user.userprofile.full_name,
                "booking": booking,
                "hosts": hostnames,
                "booking_url": os.environ.get("DASHBOARD_URL", "<Dashboard url>") + "/booking/detail/" + str(booking.id) + "/"
            }

            message = render_to_string(template_name, context)

            Email.objects.create(title="Your Booking has Expired", message=message, recipient=user.userprofile.email_addr)

    @classmethod
    def email_booking_expiring(cls, booking):
        template_name = "notifier/email_expiring.txt"
        hostnames = [host.name for host in booking.resource.get_resources()]
        users = list(booking.collaborators.all())
        users.append(booking.owner)
        for user in users:
            context = {
                "user_name": user.userprofile.full_name,
                "booking": booking,
                "hosts": hostnames,
                "booking_url": os.environ.get("DASHBOARD_URL", "<Dashboard url>") + "/booking/detail/" + str(booking.id) + "/"
            }

            message = render_to_string(template_name, context)

            Email.objects.create(title="Your Booking is Expiring", message=message, recipient=user.userprofile.email_addr)

    @classmethod
    def task_updated(cls, task):
        """
        Notification of task changing.

        called every time a lab updated info about a task.
        sends an email when 'task' changing state means a booking has
        just been fulfilled (all tasks done, servers ready to use)
        or is over.
        """
        if task.job is None or task.job.booking is None:
            return
        if task.job.is_fulfilled():
            if task.job.booking.end < timezone.now():
                if Emailed.objects.filter(end_booking=task.job.booking).exists():
                    return
                Emailed.objects.create(end_booking=task.job.booking)
                cls.email_booking_over(task.job.booking)
            if task.job.booking.end > timezone.now() and task.job.booking.start < timezone.now():
                if Emailed.objects.filter(begin_booking=task.job.booking).exists():
                    return
                Emailed.objects.create(begin_booking=task.job.booking)
                cls.email_job_fulfilled(task.job)
