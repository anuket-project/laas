# Generated by Django 2.2 on 2023-07-17 15:25

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0010_auto_20230608_1913'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='aggregateId',
            field=models.CharField(blank=True, max_length=36, validators=[django.core.validators.RegexValidator(code='nomatch', message='aggregate_id must be a valid UUID', regex='^[0-9a-fA-F]{8}\x08-[0-9a-fA-F]{4}\x08-[0-9a-fA-F]{4}\x08-[0-9a-fA-F]{4}\x08-[0-9a-fA-F]{12}$')]),
        ),
    ]
