# Generated by Django 2.2 on 2023-07-24 20:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0010_auto_20230608_1913'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='ipa_username',
            field=models.CharField(max_length=100, null=True),
        ),
    ]
