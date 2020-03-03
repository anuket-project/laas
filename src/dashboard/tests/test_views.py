##############################################################################
# Copyright (c) 2020 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.test import TestCase, Client
from dashboard.testing_utils import make_lab


class DashboardViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_lab(name="TestLab")
        cls.client = Client()

    def test_landing_view_anon(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_lab_list_view(self):
        response = self.client.get('/lab/')
        self.assertEqual(response.status_code, 200)

    def test_lab_detail_view(self):
        response = self.client.get('/lab/TestLab/')
        self.assertEqual(response.status_code, 200)
