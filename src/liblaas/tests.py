##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.test import TestCase
from liblaas.views import liblaas_docs, user_get_user

class LibLaaSTests(TestCase):
    def test_can_reach_liblaas(self):
        response = liblaas_docs()
        self.assertEqual(response.status_code, 200)

class BookingTests(TestCase):
    def test_create_booking_succeeds_with_valid_blob(self):
        pass

    def test_create_booking_fails_with_invalid_blob(self):
        pass

    def test_booking_status_succeeds_on_valid_booking_id(self):
        pass
    
    def test_end_booking_succeeds_on_valid_agg_id(self):
        pass

class FlavorTests(TestCase):
    def test_list_flavors_succeeds(self):
        pass

    def test_get_flavor_by_id_succeeds(self):
        pass

    def test_list_hosts_succeeds(self):
        pass

class TemplateTests(TestCase):
    def test_list_templates_succeeds(self):
        pass

    def test_make_template_succeeds(self):
        pass

    def test_delete_template_succeeds(self):
        pass

class UserTests(TestCase):
    def test_get_user_succeeds(self):
        pass

    def test_create_user_succeeds(self):
        pass

    def test_set_ssh_succeeds(self):
        pass

    def test_set_company_succeeds(self):
        pass

    def test_set_email_succeeds(self):
        pass
