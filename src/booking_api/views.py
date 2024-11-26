from rest_framework import viewsets, status
from booking.models import Booking
from datetime import timedelta
from .serializers import BookingSerializer
from account.models import User, UserProfile, Lab
from account.views import user_get_user
from liblaas.views import (
    booking_create_booking,
    booking_booking_status,
    booking_ipmi_setpower,
    booking_set_image,
)
from booking.lib import attempt_end_booking
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from django.utils import timezone
from datetime import timedelta, datetime
import json
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from laas_dashboard.settings import PROJECT


# endpoint booking_api/booking
class BookingViewSet(viewsets.ViewSet):
    serializer_class = BookingSerializer
    authentication_classes = [TokenAuthentication]
    queryset = Booking.objects.all()
    permission_classes = [IsAuthenticated]

    def list(self, request:HttpRequest):
        if self.request.user.is_authenticated:
            user = self.request.user
            query_parameter = self.request.query_params.get('active')
            if query_parameter == 'True':
                active = True
            else:
                active = False
            bookings_of_user = Booking.objects.filter(owner=user)
            lst_of_serial_booking: list = []
            for booking in bookings_of_user:
                if active:
                    if not booking.complete:
                        owned_serilized_booking = BookingSerializer(booking)
                        lst_of_serial_booking.append(owned_serilized_booking.data)
                else:    
                    owned_serilized_booking = BookingSerializer(booking)
                    lst_of_serial_booking.append(owned_serilized_booking.data)
            serilized_list_of_booking = json.dumps(lst_of_serial_booking)
            if not lst_of_serial_booking:
                return Response(data="no bookings", status=status.HTTP_200_OK)
            else:
                return Response(
                    data=serilized_list_of_booking, status=status.HTTP_200_OK
                )
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

    def create(self, request: HttpRequest):
        if self.request.user.is_authenticated:
            booking_response = None
            data = self.request.data
            allowed_users = list(data["allowed_users"])
            ipa_users = allowed_users
            booking_blob = {
                "template_id": data["template_id"],
                "allowed_users": ipa_users,
                "global_cifile": data["global_cifile"],
                "metadata": {
                    "booking_id": str(None),
                    "owner": UserProfile.objects.get(
                        user=self.request.user
                    ).ipa_username,
                    "lab": PROJECT,
                    "purpose": data["metadata"]["purpose"],
                    "project": data["metadata"]["project"],
                    "length": int(data["metadata"]["length"]),
                },
                "origin": PROJECT,
            }
            # Dashboard booking
            booking = Booking.objects.create(
                purpose=booking_blob["metadata"]["purpose"],
                project=booking_blob["metadata"]["project"],
                lab=Lab.objects.get(name="UNH_IOL"),
                owner=self.request.user,
                start=timezone.now(),
                end=timezone.now()
                + timedelta(days=int(booking_blob["metadata"]["length"])),
            )
            for booking_collaborator in allowed_users:
                try:
                    booking.collaborators.add(
                        User.objects.get(username=booking_collaborator)
                    )
                    booking.save()
                except ObjectDoesNotExist:
                    print("collaborators not found")
            booking_blob["metadata"]["booking_id"] = str(booking.id)
            booking_response = booking_create_booking(booking_blob)
            booking.aggregateId = booking_response
            booking.save()
            if booking_response is None:
                return Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            else:

                return Response(booking_response, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)


# Gets specific booking based on id
# Deletes specific booking based on id
# endpoint booking_api/booking/{booking_id}
class BookingIdViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get_booking(self, request: HttpRequest, **kwargs):
        if self.request.user.is_authenticated:
            booking_id = self.kwargs["booking_id"]
            try:
                data = Booking.objects.get(id=booking_id)
            except ObjectDoesNotExist as e:
                print(e)
                return Response(status=status.HTTP_400_BAD_REQUEST)
            serialized_booking = BookingSerializer(data)
            if data is not None:
                return Response(
                    data=json.dumps(serialized_booking.data), status=status.HTTP_200_OK
                )
            else:
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

    def destroy(self, request: HttpRequest, **kwargs):
        if self.request.user.is_authenticated:
            booking_id = self.kwargs["booking_id"]
            try:
                booking = Booking.objects.get(id=booking_id)
            except ObjectDoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            if self.request.user == booking.owner:
                booking.end = timezone.now()
                booking.save()
                response_end_booking = attempt_end_booking(booking=booking)
                if response_end_booking[0] == False:
                    return Response(
                        data=None, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                else:
                    res_json = json.dumps(response_end_booking[1])
                    return Response(data=res_json, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)


# Gets status of a booking based on id (includes logs)
# endpoint booking_api/booking/{booking_id}/status
class BookingIdStatusViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get_status(self, request: HttpRequest, **kwargs):
        if self.request.user.is_authenticated:
            try:
                booking = Booking.objects.get(id=self.kwargs["booking_id"])
            except ObjectDoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            agg_id = booking.aggregateId
            booking_status = booking_booking_status(agg_id=agg_id)
            if booking_status is None:
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                booking_status_json = json.dumps(booking_status)
                return Response(data=booking_status_json, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)


# Gets collaborators of a specific booking
# Adds collaborators to a specific booking
# endpoint booking_api/booking/{booking_id}/collaborators
class BookingIdCollaboratorsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get_collaborators(
        self, request: HttpRequest, *args, **kwargs
    ):
        if self.request.user.is_authenticated:
            full = self.request.query_params.get('full')
            if full == "True":
                full = True
            else:
                full = False
            booking_id = self.kwargs["booking_id"]
            try:
                booking = Booking.objects.get(id=booking_id)
            except ObjectDoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            lst_collaborators = []
            queries = booking.collaborators.all()
            booking_collaborators = []
            for x in queries:
                booking_collaborators.append(x)
            if len(booking_collaborators) == 0:
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                for collaborator in booking_collaborators:
                    dict_collaborators = dict.fromkeys(
                        ["dashboard_username", "vpn_username", "company", "email"]
                    )
                    curr_collaborator = UserProfile.objects.get(user=collaborator)
                    collaborator_ipa_name = curr_collaborator.ipa_username
                    dict_collaborators.update({"vpn_username": collaborator_ipa_name})
                    if not full:
                        collaborator_company = user_get_user(
                            curr_collaborator.ipa_username
                        )
                        if collaborator_company:
                            collaborator_company = (
                                collaborator_company["ou"]
                                if "ou" in collaborator_company
                                else ""
                            )
                        else:
                            collaborator_company = "UNKNOWN"
                        dict_collaborators.update({"company": collaborator_company})
                    collaborator_dashboard_name = curr_collaborator.user.username
                    dict_collaborators.update(
                        {"dashboard_username": collaborator_dashboard_name}
                    )
                    collaborator_email = curr_collaborator.email_addr
                    dict_collaborators.update({"email": collaborator_email})
                    lst_collaborators.append(dict_collaborators)
                    json_lst_collaborators = json.dumps(lst_collaborators)
                return Response(data=json_lst_collaborators, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

    def post(self, request: HttpRequest, **kwargs):
        if self.request.user.is_authenticated:
            try:
                booking = Booking.objects.get(id=kwargs["booking_id"])
            except ObjectDoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            if self.request.user == booking.owner and self.request.data is not None:
                for user in list(self.request.data["id"]):
                    try:
                        django_user = User.objects.get(username=user)
                        booking.collaborators.add(django_user)
                        booking.save()
                    except ObjectDoesNotExist:
                        print("object not found")
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)


# Sets power setting for specific instance.
# Command options: PowerOn, PowerOff, Restart
# endpoint /booking/{booking_id}/instance/{intance_id}/power
class BookingIdInstanceIdPowerViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def power(self, **kwargs):
        if self.request.user.is_authenticated:
            host_id = self.kwargs["booking_id"]
            command = self.request.data
            r_data = booking_ipmi_setpower(
                host_id=self.kwargs["instance_id"], command=command
            )
            if r_data is not None:
                return Response(data=r_data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)


# Reprovisions instance based on image name and instance id
# endpoint booking_api/booking/{booking_id}/instance/{intance_id}/reprovision
class BookingIdInstanceIdReprovisionViewSet(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def reprovision(self, **kwargs):
        if self.request.user.is_authenticated:
            try:
                booking = Booking.objects.get(id=kwargs["booking_id"])
            except ObjectDoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            if self.request.user == booking.owner:
                response = booking_set_image(
                    instance_key=kwargs["instance_id"],
                    image={"image_id": self.request.data["image"]},
                )
                print(response)
                if response["code"] == 500 or response is None:
                    return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                elif response["code"] == 200:
                    return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)


# Extends booking time on the dashboard
# endpoint booking_api/booking/{booking_id}/extend
class BookingIdExtend(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def extend(self, request: HttpRequest, **kwargs):
        if self.request.user.is_authenticated:
            try:
                booking = Booking.objects.get(id=self.kwargs["booking_id"])
            except ObjectDoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            if booking.owner == self.request.user:
                ext_days_left = booking.ext_days
                requested_ext_days = self.request.data["data"]
                requested_ext_days = int(requested_ext_days)
                if requested_ext_days > ext_days_left or requested_ext_days < 0:
                    return Response(status=status.HTTP_409_CONFLICT)
                else:
                    booking.ext_days -= requested_ext_days
                    booking.end += timedelta(requested_ext_days)
                    booking.save()
                    return Response(status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
            
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
