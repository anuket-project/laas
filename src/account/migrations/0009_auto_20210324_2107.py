# Generated by Django 2.2 on 2021-03-24 21:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0008_auto_20210324_2106'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='public_user',
            field=models.BooleanField(default=False),
        ),
    ]