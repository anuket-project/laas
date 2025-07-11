# Generated by Django 5.0 on 2025-07-08 16:16

from django.db import migrations, models
from booking.models import Booking


def forward_purpose_to_details(apps, schema_editor):
    bookings: Booking = apps.get_model("booking", "booking")
    for booking in bookings.objects.all().iterator():
        booking.details = booking.purpose
        booking.save()


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0015_booking_details'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='details',
            field=models.TextField(blank=False),
        ),
        migrations.RunPython(forward_purpose_to_details, migrations.RunPython.noop("booking", None))
    ]
