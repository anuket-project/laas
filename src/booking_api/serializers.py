from rest_framework import serializers
from account.models import User, UserProfile
from booking.models import Booking

# class UserSerializer(serializers.Serializer):


class BookingSerializer(serializers.Serializer):
    # all fields below or serializer
    id = serializers.IntegerField()
    owner = serializers.CharField()
    collaborators = serializers.ListSerializer(child=serializers.CharField())
    start = serializers.CharField()
    end = serializers.CharField()
    purpose = serializers.CharField()
    ext_days = serializers.IntegerField()
    project = serializers.CharField()
    aggregateId = serializers.CharField()
    complete = serializers.BooleanField()

    class Meta:
        model = Booking
        fields = {
            "id",
            "owner",
            "collaborators",
            "start",
            "end",
            "purpose",
            "extension_days",
            "project",
            "aggreegateId",
            "complete",
        }

