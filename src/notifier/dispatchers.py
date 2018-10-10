##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib import messages
from django.core.mail import send_mail

class DispatchHandler():

    @receiver(pre_save, sender='notifier.Notifier')
    def dispatch(sender, instance, *args, **kwargs):
        try:
            msg_type = getattr(DispatchHandler, instance.message_type)
            msg_type(instance)
        except AttributeError:
            instance.msg_sent = 'no dispatcher by given name exists: sending by email'
            email(instance)

    def email(instance):
        if instance.msg_sent != 'no dispatcher by given name exists: sending by email':
            instance.msg_sent = 'by email'
        send_mail(instance.title,instance.content,
            instance.sender,[instance.user.email_addr], fail_silently=False)

    def webnotification(instance):
        instance.msg_sent='by web notification'
