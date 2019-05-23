##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

import datetime

from django.test import TestCase, Client

from booking.models import Booking
from dashboard.testing_utils import (
    make_host,
    make_user,
    make_user_profile,
    make_lab,
    make_installer,
    make_image,
    make_scenario,
    make_os,
    make_complete_host_profile,
    make_opnfv_role,
    make_public_net,
)


class QuickBookingValidFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user(False, username="newtestuser", password="testpassword")
        make_user_profile(cls.user, True)

        lab_user = make_user(True)
        cls.lab = make_lab(lab_user)

        cls.host_profile = make_complete_host_profile(cls.lab)
        cls.scenario = make_scenario()
        cls.installer = make_installer([cls.scenario])
        os = make_os([cls.installer])
        cls.image = make_image(cls.lab, 1, cls.user, os, cls.host_profile)
        cls.host = make_host(cls.host_profile, cls.lab)
        cls.role = make_opnfv_role()
        cls.pubnet = make_public_net(10, cls.lab)

        cls.post_data = cls.build_post_data()
        cls.client = Client()

    @classmethod
    def build_post_data(cls):
        return {
            'filter_field': '{"hosts":[{"host_' + str(cls.host_profile.id) + '":"true"}], "labs": [{"lab_' + str(cls.lab.lab_user.id) + '":"true"}]}',
            'purpose': 'my_purpose',
            'project': 'my_project',
            'length': '3',
            'ignore_this': 1,
            'users': '',
            'hostname': 'my_host',
            'image': str(cls.image.id),
            'installer': str(cls.installer.id),
            'scenario': str(cls.scenario.id)
        }

    def post(self, changed_fields={}):
        payload = self.post_data.copy()
        payload.update(changed_fields)
        response = self.client.post('/booking/quick/', payload)
        return response

    def setUp(self):
        self.client.login(username=self.user.username, password="testpassword")

    def assertValidBooking(self, booking):
        self.assertEqual(booking.owner, self.user)
        self.assertEqual(booking.purpose, 'my_purpose')
        self.assertEqual(booking.project, 'my_project')
        delta = booking.end - booking.start
        delta -= datetime.timedelta(days=3)
        self.assertLess(delta, datetime.timedelta(minutes=1))

        resource_bundle = booking.resource
        config_bundle = booking.config_bundle

        opnfv_config = config_bundle.opnfv_config.first()
        self.assertEqual(self.installer, opnfv_config.installer)
        self.assertEqual(self.scenario, opnfv_config.scenario)

        host = resource_bundle.hosts.first()
        self.assertEqual(host.profile, self.host_profile)
        self.assertEqual(host.template.resource.name, 'my_host')

    def test_with_too_long_length(self):
        response = self.post({'length': '22'})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Booking.objects.first())

    def test_with_negative_length(self):
        response = self.post({'length': '-1'})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Booking.objects.first())

    def test_with_invalid_installer(self):
        response = self.post({'installer': str(self.installer.id + 100)})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Booking.objects.first())

    def test_with_invalid_scenario(self):
        response = self.post({'scenario': str(self.scenario.id + 100)})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Booking.objects.first())

    def test_with_invalid_host_id(self):
        response = self.post({'filter_field': '{"hosts":[{"host_' + str(self.host_profile.id + 100) + '":"true"}], "labs": [{"lab_' + str(self.lab.lab_user.id) + '":"true"}]}'})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Booking.objects.first())

    def test_with_invalid_lab_id(self):
        response = self.post({'filter_field': '{"hosts":[{"host_' + str(self.host_profile.id) + '":"true"}], "labs": [{"lab_' + str(self.lab.lab_user.id + 100) + '":"true"}]}'})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Booking.objects.first())

    def test_with_invalid_empty_filter_field(self):
        response = self.post({'filter_field': ''})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Booking.objects.first())

    def test_with_garbage_users_field(self):  # expected behavior: treat as though field is empty if it has garbage data
        response = self.post({'users': 'X�]QP�槰DP�+m���h�U�_�yJA:.rDi��QN|.��C��n�P��F!��D�����5ȅj�9�LV��'})  # output from /dev/urandom

        self.assertEqual(response.status_code, 200)
        booking = Booking.objects.first()
        self.assertIsNotNone(booking)
        self.assertValidBooking(booking)

    def test_with_valid_form(self):
        response = self.post()

        self.assertEqual(response.status_code, 200)
        booking = Booking.objects.first()
        self.assertIsNotNone(booking)
        self.assertValidBooking(booking)
