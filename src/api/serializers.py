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
from booking.models import Booking
from dashboard.models import Server, Resource, ResourceStatus

class BookingSerializer(serializers.ModelSerializer):
    installer_name = serializers.CharField(source='installer.name')
    scenario_name = serializers.CharField(source='scenario.name')
    opsys_name = serializers.CharField(source='opsys.name')

    class Meta:
        model = Booking
        fields = ('id', 'changeid', 'reset', 'user', 'resource_id', 'opsys_name', 'start', 'end', 'installer_name', 'scenario_name', 'purpose')


class ServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Server
        fields = ('id', 'resource_id', 'name', 'model', 'cpu', 'ram', 'storage')


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ('id', 'name', 'description', 'resource_lab', 'url', 'server_set', 'dev_pod')

class ResourceStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceStatus
        fields = ('id', 'resource', 'timestamp','type', 'title', 'content')

class NotifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notifier
        fields = ('id', 'title', 'content', 'user', 'sender', 'message_type', 'msg_sent')

class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    class Meta:
        model = UserProfile
        fields = ('user', 'username', 'ssh_public_key', 'pgp_public_key', 'email_addr')
