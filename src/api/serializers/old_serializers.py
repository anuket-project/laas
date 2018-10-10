##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from rest_framework import serializers

from account.models import UserProfile
from notifier.models import Notifier


class NotifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notifier
        fields = ('id', 'title', 'content', 'user', 'sender', 'message_type', 'msg_sent')


class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')

    class Meta:
        model = UserProfile
        fields = ('user', 'username', 'ssh_public_key', 'pgp_public_key', 'email_addr')
