# Generated by Django 2.2 on 2023-06-08 19:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0009_booking_complete'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='booking',
            name='jira_issue_id',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='jira_issue_status',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='opnfv_config',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='resource',
        ),
    ]
