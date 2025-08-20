from django.test import TestCase, override_settings
from django.core import mail
from django.utils import timezone
from booking.models import Booking, AbstractScheduledNotification
from account.models import User, Lab
from dashboard import tasks
from unittest.mock import patch, MagicMock
import datetime


class FailSendNotification(AbstractScheduledNotification):
    # Fails to send
    def _send(self):
        return False

class SuccessNotification(AbstractScheduledNotification):
    # 'Sends' successfully
    def _send(self):
        return True


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, SITE_CONTACT="", LIBLAAS_BASE_URL="")
class CeleryTests(TestCase):


    expired_bookings = 0
    @classmethod
    def setUpTestData(cls):
        testUser = User.objects.create_user("testuser", "test@email.com", "testpass")
        beginningOfTime = datetime.datetime(datetime.MINYEAR, 1, 1, 1, tzinfo=timezone.get_current_timezone())
        littleAfter = datetime.datetime(datetime.MINYEAR, 1, 2, tzinfo=timezone.get_current_timezone())
        endOfTime = datetime.datetime(datetime.MAXYEAR, 1, 1, tzinfo=timezone.get_current_timezone())
        
        
        lab = Lab.objects.create(
            name="TestLab",
            contact_email="test@email.com",
            location="Test Location",
            description="Test Description",
            project="Test Project",
            lab_user=User.objects.create_user("admin"),
            about_text="Test about us text"
        )

        Booking.objects.create(
            owner=testUser,
            start=beginningOfTime,
            end=endOfTime,
            purpose="valid",
            project="valid",
            lab=lab,
            aggregateId="uselessAggregateId",
        )


        Booking.objects.create(
            owner=testUser,
            start=beginningOfTime,
            end=littleAfter,
            purpose="invalid",
            project="invalid",
            lab=lab,
            aggregateId="uselessAggregateId",
        )


        for booking in Booking.objects.iterator():
            if (booking.end < datetime.datetime.now(tz=timezone.get_current_timezone())):
                cls.expired_bookings += 1
                FailSendNotification.objects.create(when=datetime.datetime.now(tz=timezone.get_current_timezone()), sent=False)

                        
    @patch('dashboard.tasks.attempt_end_booking')
    def test_end_expired_bookings(self, mock_func: MagicMock):
        # Ensure error was caught, created an email, and the correct number of bookings was attempted to be deleted
        
        mock_func.side_effect = RuntimeError("This mock function always errors")
        
        assert mock_func is tasks.attempt_end_booking, "Some functionality to celery or mock functions has changed in an update"

        tasks.end_expired_bookings()

        self.assertEqual(len(mail.outbox), self.expired_bookings)  
        self.assertEqual(mock_func.call_count, self.expired_bookings)


    def test_send_notifications(self):

        tasks.send_notifications()
        self.assertEqual(len(mail.outbox), self.expired_bookings)
        