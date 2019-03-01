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
    instantiate_host,
    instantiate_user,
    instantiate_userprofile,
    instantiate_lab,
    instantiate_installer,
    instantiate_image,
    instantiate_scenario,
    instantiate_os,
    make_hostprofile_set,
    instantiate_opnfvrole,
    instantiate_publicnet,
)
# from dashboard import test_utils


class QuickBookingValidFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.loginuser = instantiate_user(False, username="newtestuser", password="testpassword")
        instantiate_userprofile(cls.loginuser, True)

        lab_user = instantiate_user(True)
        cls.lab = instantiate_lab(lab_user)

        cls.host_profile = make_hostprofile_set(cls.lab)
        cls.scenario = instantiate_scenario()
        cls.installer = instantiate_installer([cls.scenario])
        os = instantiate_os([cls.installer])
        cls.image = instantiate_image(cls.lab, 1, cls.loginuser, os, cls.host_profile)
        cls.host = instantiate_host(cls.host_profile, cls.lab)
        cls.role = instantiate_opnfvrole()
        cls.pubnet = instantiate_publicnet(10, cls.lab)

        cls.lab_selected = 'lab_' + str(cls.lab.lab_user.id) + '_selected'
        cls.host_selected = 'host_' + str(cls.host_profile.id) + '_selected'

        cls.post_data = cls.build_post_data()

        cls.client = Client()

    @classmethod
    def build_post_data(cls):
        post_data = {}
        post_data['filter_field'] = '{"hosts":[{"host_' + str(cls.host_profile.id) + '":"true"}], "labs": [{"lab_' + str(cls.lab.lab_user.id) + '":"true"}]}'
        post_data['purpose'] = 'purposefieldcontentstring'
        post_data['project'] = 'projectfieldcontentstring'
        post_data['length'] = '3'
        post_data['ignore_this'] = 1
        post_data['users'] = ''
        post_data['hostname'] = 'hostnamefieldcontentstring'
        post_data['image'] = str(cls.image.id)
        post_data['installer'] = str(cls.installer.id)
        post_data['scenario'] = str(cls.scenario.id)
        return post_data

    def post(self, changed_fields={}):
        payload = self.post_data.copy()
        payload.update(changed_fields)
        response = self.client.post('/booking/quick/', payload)
        return response

    def setUp(self):
        self.client.login(
            username=self.loginuser.username, password="testpassword")

    def is_valid_booking(self, booking):
        self.assertEqual(booking.owner, self.loginuser)
        self.assertEqual(booking.purpose, 'purposefieldcontentstring')
        self.assertEqual(booking.project, 'projectfieldcontentstring')
        delta = booking.end - booking.start
        delta -= datetime.timedelta(days=3)
        self.assertLess(delta, datetime.timedelta(minutes=1))

        resourcebundle = booking.resource
        configbundle = booking.config_bundle

        self.assertEqual(self.installer, configbundle.opnfv_config.first().installer)
        self.assertEqual(self.scenario, configbundle.opnfv_config.first().scenario)
        self.assertEqual(resourcebundle.template.getHosts()[0].profile, self.host_profile)
        self.assertEqual(resourcebundle.template.getHosts()[0].resource.name, 'hostnamefieldcontentstring')

        return True

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
        self.assertTrue(self.is_valid_booking(booking))

    def test_with_valid_form(self):
        response = self.post()

        self.assertEqual(response.status_code, 200)
        booking = Booking.objects.first()
        self.assertIsNotNone(booking)
        self.assertTrue(self.is_valid_booking(booking))
