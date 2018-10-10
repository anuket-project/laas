##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
from django.test import TestCase, Client

class SuperViewTestCase(TestCase):
    url = "/"
    client = Client()

    def test_get(self):
        response = self.client.get(self.url)
        self.assertLess(response.status_code, 300)


class DefineHardwareViewTestCase(SuperViewTestCase):
    url = "/wf/workflow/step/define_hardware"

class DefineNetworkViewTestCase(SuperViewTestCase):
    url = "/wf/workflow/step/define_net"

class ResourceMetaViewTestCase(SuperViewTestCase):
    url = "/wf/workflow/step/resource_meta"

class BookingMetaViewTestCase(SuperViewTestCase):
    url = "/wf/workflow/step/booking_meta"

class SoftwareSelectViewTestCase(SuperViewTestCase):
    url = "/wf/workflow/step/software_select"

class ResourceSelectViewTestCase(SuperViewTestCase):
    url = "/wf/workflow/step/resource_select"
