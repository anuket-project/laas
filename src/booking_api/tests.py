from django.test import TestCase, Client
from booking.models import Booking
from account.models import UserProfile, User, Lab
from rest_framework import status
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from rest_framework.authtoken.models import Token
import json
from unittest.mock import patch


# from liblaas import views
class BookingViewSetTestCase(TestCase):
    # NOTE: Set up test data only runs once where set up runs for each test
    @classmethod
    def setUpTestData(cls) -> None:
        print(
            "\nTESTING all endpoints excluding power and reprovision as they require tacii to assign instance id\n"
        )
        user = User.objects.create(username="test")
        user_profile = UserProfile.objects.create(user=user)
        collaborator = User.objects.create(username="collaborator")
        collaborator = UserProfile.objects.create(user=collaborator)
        now = timezone.now()
        tomorrow = now + timedelta(10)
        lab = Lab.objects.create(name="UNH_IOL", lab_user=user)
        cls.booking = Booking.objects.create(
            owner=user, start=now, end=tomorrow, purpose="test", project="test", lab=lab
        )
        cls.booking.collaborators.add(user)

    def setUp(self):
        self.user = User.objects.get(username="test")
        token = Token.objects.get(user=self.user)
        self.client = Client(headers={"Authorization": f"Token {token}"})
        self.booking = Booking.objects.get(owner=self.user)

    # endpoint /booking
    @patch("booking_api.views.booking_create_booking")
    def test_booking(self, booking_create_booking_mock):
        response: Response = self.client.get(
            "http://127.0.0.1:8000/booking_api/booking/"
        )
        response_data = json.loads(response.data)
        response_dict_of_get_data: dict = {}
        for booking in response_data:
            response_dict_of_get_data.update(booking)
        # figure out how to access the class data
        expected_response_get_data = {
            "id": self.booking.id,
            "owner": "test",
            "collaborators": ["test"],
            "purpose": "test",
            "project": "test",
        }
        self.assertEqual(
            expected_response_get_data["id"], response_dict_of_get_data["id"]
        )
        self.assertEqual(
            expected_response_get_data["owner"], response_dict_of_get_data["owner"]
        )
        self.assertEqual(
            expected_response_get_data["collaborators"],
            response_dict_of_get_data["collaborators"],
        )
        self.assertEqual(
            expected_response_get_data["purpose"], response_dict_of_get_data["purpose"]
        )
        self.assertEqual(
            expected_response_get_data["project"], response_dict_of_get_data["project"]
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking_blob = {
            "template_id": " ",
            "allowed_users": ["test", "collaborator"],
            "global_cifile": "",
            "metadata": {
                "purpose": "test",
                "project": "test",
                "length": "1",
            },
        }
        booking_create_booking_mock.return_value = "success"
        json_booking_blob = json.dumps(booking_blob)
        response: Response = self.client.post(
            "http://127.0.0.1:8000/booking_api/booking/",
            data=json_booking_blob,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response: Response = self.client.get(
            "http://127.0.0.1:8000/booking_api/booking/"
        )
        response_data = json.loads(response.data)
        response_data_added_booking = response_data[1]
        # Check to see if second booking was added and if get still works with two bookings
        expected_response_added_booking = {
            "id": self.booking.id + 1,
            "owner": "test",
            "collaborators": ["test", "collaborator"],
            "purpose": "test",
            "project": "test",
        }
        self.assertEqual(
            expected_response_added_booking["id"], response_data_added_booking["id"]
        )
        self.assertEqual(
            expected_response_added_booking["owner"],
            response_data_added_booking["owner"],
        )
        self.assertEqual(
            expected_response_added_booking["collaborators"],
            response_data_added_booking["collaborators"],
        )
        self.assertEqual(
            expected_response_added_booking["purpose"],
            response_data_added_booking["purpose"],
        )
        self.assertEqual(
            expected_response_added_booking["project"],
            response_data_added_booking["project"],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # endpoint /booking/booking_id/extend
    def test_booking_id_extend(self):
        json_string = {"data": "1 "}
        json_data = json.dumps(json_string)
        response: Response = self.client.post(
            f"http://127.0.0.1:8000/booking_api/booking/{self.booking.id}/extend/",
            json_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # endpoint /booking/booking_id/collaborators
    def test_booking_id_collaborators(self):
        response: Response = self.client.get(
            path=f"http://127.0.0.1:8000/booking_api/booking/{self.booking.id}/collaborators/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Data to add 'collaborator'
        data = {"id": ["test", "collaborator"]}
        json_data = json.dumps(data)
        response = self.client.post(
            f"http://127.0.0.1:8000/booking_api/booking/{self.booking.id}/collaborators/",
            data=json_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        bad_data = {"id": ["bad_user"]}
        json_bad_data = json.dumps(bad_data)
        response = self.client.post(
            f"http://127.0.0.1:8000/booking_api/booking/{self.booking.id}/collaborators/",
            data=json_bad_data,
            content_type="application/json",
        )
        response_after_bad_data = self.client.get(
            path=f"http://127.0.0.1:8000/booking_api/booking/{self.booking.id}/collaborators/"
        ).data
        expected_response_data = [
            {
                "dashboard_username": "test",
                "vpn_username": None,
                "company": 'UNKNOWN',
                "email": "email@mail.com",
            },
            {
                "dashboard_username": "collaborator",
                "vpn_username": None,
                "company": 'UNKNOWN',
                "email": "email@mail.com",
            },
        ]
        # Test to ensure that after adding the collabortor and attempting to add bad data that only the two collaborators are there
        self.assertEqual(json.loads(response_after_bad_data), expected_response_data)

    # endpoint /booking/booking_id/status
    @patch("booking_api.views.booking_booking_status")
    def test_booking_id_status(self, mock_booking_booking_status):
        mock_booking_booking_status.return_value = "MOCKING success from tascii"
        response: Response = self.client.get(
            f"http://127.0.0.1:8000/booking_api/booking/{self.booking.id}/status/"
        )
        # print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # endpoint /booking/booking_id
    @patch("booking_api.views.booking_end_booking")
    def test_booking_id(self, mock_booking_end_booking):
        response: Response = self.client.get(
            f"http://127.0.0.1:8000/booking_api/booking/{self.booking.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_response = {
            "id": self.booking.id,
            "owner": "test",
            "collaborators": ["test"],
            "purpose": "test",
            "project": "test",
            "complete": False,
        }
        response_loaded_json = json.loads(response.data)
        self.assertEqual(expected_response["id"], response_loaded_json["id"])
        self.assertEqual(expected_response["owner"], response_loaded_json["owner"])
        self.assertEqual(
            expected_response["collaborators"], response_loaded_json["collaborators"]
        )
        self.assertEqual(expected_response["purpose"], response_loaded_json["purpose"])
        self.assertEqual(expected_response["project"], response_loaded_json["project"])
        self.assertEqual(
            expected_response["complete"], response_loaded_json["complete"]
        )
        # Test delete (DELETE DOES NOT DELETE DJANGO OBJECT!!!)
        mock_booking_end_booking.return_value = "success from tascii"
        response_delete: Response = self.client.delete(
            f"http://127.0.0.1:8000/booking_api/booking/{self.booking.id}/"
        )
        self.assertEqual(response_delete.status_code, status.HTTP_200_OK)

