##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from unittest import SkipTest
from django.test import TestCase
from workflow.workflow_factory import WorkflowFactory


"""
To start a workflow:
    POST to /wf/workflow {"add": <wf_type_int>

    types:
        0 - Booking
        1 - Resource
        2 - Config

To remove a workflow:
    POST to /wf/workflow {"cancel": ""}
"""


class WorkflowTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        raise SkipTest("These tests are no good")

    def setUp(self):
        self.clear_workflow()
        self.create_workflow(self.wf_type)

    def create_workflow(self, wf_type):
        self.clear_workflow()

        # creates workflow on backend
        self.client.post("/", {"create": int(wf_type)})  # TODO: verify content type, etc

    def clear_workflow(self):
        session = self.client.session
        for k in session.keys():
            del session[k]
        session.save()

    def render_steps(self):
        """
        retrieves each step individually at /wf/workflow/step=<index>
        """
        for i in range(self.step_count):
            #  renders the step itself, not in an iframe
            exception = None
            try:
                response = self.client.get("/wf/workflow/", {"step": str(i)})
                self.assertLess(response.status_code, 300)
            except Exception as e:
                exception = e

            self.assertIsNone(exception)


class BookingWorkflowTestCase(WorkflowTestCase):

    @classmethod
    def setUpClass(cls):
        super(BookingWorkflowTestCase, cls).setUpClass()
        cls.step_count = len(WorkflowFactory.booking_steps)
        cls.wf_type = 0

    def test_steps_render(self):
        super(BookingWorkflowTestCase, self).render_steps()


class ResourceWorkflowTestCase(WorkflowTestCase):

    @classmethod
    def setUpClass(cls):
        super(ResourceWorkflowTestCase, cls).setUpClass()
        cls.step_count = len(WorkflowFactory.resource_steps)
        cls.wf_type = 1

    def test_steps_render(self):
        super(ResourceWorkflowTestCase, self).render_steps()


class ConfigWorkflowTestCase(WorkflowTestCase):

    @classmethod
    def setUpClass(cls):
        super(ConfigWorkflowTestCase, cls).setUpClass()
        cls.step_count = len(WorkflowFactory.config_steps)
        cls.wf_type = 2

    def test_steps_render(self):
        super(ConfigWorkflowTestCase, self).render_steps()
