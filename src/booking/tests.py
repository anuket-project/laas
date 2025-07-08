from django.test import TestCase

from booking.models import Booking, ExpiringBookingNotification
from account.models import UserProfile
from django.contrib.auth.models import User
from account.models import Lab
from django.utils import timezone
from datetime import timedelta

class SchemaTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner1 = UserProfile.objects.create(
            user=User.objects.create_user(
            f"owner1",
            f"owner1@email.com",
            f"testpassword",
            )
        )
        
        cls.c1 = UserProfile.objects.create(
            user=User.objects.create_user(
            f"c1",
            f"c1@email.com",
            f"testpassword",
            )
        )

        cls.c2 = UserProfile.objects.create(
            user=User.objects.create_user(
            f"c2",
            f"c2@email.com",
            f"testpassword",
            )
        )
        
        cls.lab = Lab.objects.create(
            name="TestLab",
            contact_email="test@email.com",
            location="Test Location",
            description="Test Description",
            project="Test Project",
            lab_user=User.objects.create_user("admin")
        )
        
    def test_create_booking(self):
        owner = self.owner1.user
        start = timezone.now()
        end = start + timedelta(days=10)
        purpose = "Test Purpose",
        project = "Test Project"
        lab = self.lab

        booking = Booking.create_booking(
            owner,
            start,
            end,
            purpose,
            project,
            lab
        )
        
        self.assertEqual(owner, booking.owner)
        self.assertEqual(start, booking.start)
        self.assertEqual(end, booking.end)
        self.assertEqual(project, booking.project)
        self.assertEqual(purpose, booking.purpose)
        self.assertEqual(lab, booking.lab)
        self.assertEqual(len(booking.collaborators.all()), 0)

    def test_create_booking_with_collaborators(self):
        booking = Booking.create_booking(
            self.owner1.user,
            timezone.now(),
            timezone.now() + timedelta(days=1),
            "test",
            "test",
            self.lab,
            collaborators=[self.c1.user, self.c2.user]
        )

        self.assertEqual(len(booking.collaborators.all()), 2)

    def test_on_booking_creation_schedule_expiring_notifications(self):
        start = timezone.now()

        shortest = Booking.create_booking(
            self.owner1.user,
            start,
            start + timedelta(days=1),
            purpose="",
            project="",
            lab=self.lab
        )
        
        short = Booking.create_booking(
            self.owner1.user,
            start,
            start + timedelta(days=3),
            purpose="",
            project="",
            lab=self.lab
        )
        
        medium = Booking.create_booking(
            self.owner1.user,
            start,
            start + timedelta(days=5),
            purpose="",
            project="",
            lab=self.lab
        )
        
        long = Booking.create_booking(
            self.owner1.user,
            start,
            start + timedelta(days=10),
            purpose="",
            project="",
            lab=self.lab
        )
        
        self.assertEqual(len(ExpiringBookingNotification.objects.filter(for_booking=shortest)), 0)
        self.assertEqual(len(ExpiringBookingNotification.objects.filter(for_booking=short)), 1)
        self.assertEqual(len(ExpiringBookingNotification.objects.filter(for_booking=medium)), 2)
        self.assertEqual(len(ExpiringBookingNotification.objects.filter(for_booking=long)), 3)