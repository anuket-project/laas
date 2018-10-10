##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
from django.test import TestCase, client
from dashboard.populate_db import Populator
from workflow.tests import constants
from workflow.workflow_factory import WorkflowFactory
from workflow.models import Repository
from workflow.resource_bundle_workflow import *
from workflow.sw_bundle_workflow import *
from workflow.booking_workflow import *
from django.http import QueryDict, HttpRequest
from django.contrib.auth.models import User
from django.core.management import call_command
from resource_inventory.models import *


class BaseStepTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        Populator().populate()

    def makeRepo(self):
        repo = Repository()
        repo.el[repo.SESSION_USER] = User.objects.filter(username="user 1").first()
        return repo

    def step_test(self, step_type, data):
        step = WorkflowFactory().make_step(step_type, self.makeRepo())
        formData = QueryDict(mutable=True)
        formData.update(data)
        request = HttpRequest()
        request.POST = formData
        response = step.post_render(request)
        context = step.get_context()
        return response, context


class BookingResourceSelectTestCase(BaseStepTestCase):

    def test_step_with_good_data(self):
        grb_model = GenericResourceBundle.objects.filter(owner__username="user 1").first()
        grb = [{"small_name": grb_model.name, "expanded_name": "user 1", "id": grb_model.id, "string": ""}]
        grb = str(grb).replace("'", '"')
        data = {"generic_resource_bundle": grb }
        response, context = self.step_test(Booking_Resource_Select, data)
        self.assertTrue(True)

    def test_step_with_bad_data(self):  # TODO
        data = {}
        response, context = self.step_test(Booking_Resource_Select, data)

    def test_step_with_empty_data(self):
        data = {}
        response, context = self.step_test(SWConfig_Select, data)

class SoftwareConfigSelectTestCase(BaseStepTestCase):

    def test_step_with_good_data(self):
        config_model = ConfigBundle.objects.filter(owner__username="user 1").first()
        config = [{"expanded_name":"user 1", "small_name":config_model.name, "id":config_model.id, "string":""}]
        config = str(config).replace("'", '"')
        data = {"software_bundle": config}
        response, context = self.step_test(SWConfig_Select, data)

    def test_step_with_bad_data(self):  # TODO
        data = {}
        response, context = self.step_test(SWConfig_Select, data)

    def test_step_with_empty_data(self):
        data = {}
        response, context = self.step_test(SWConfig_Select, data)

class BookingMetaTestCase(BaseStepTestCase):

    def test_step_with_good_data(self):
        data = {"length": 7, "project": "LaaS", "purpose": "testing"}
        user2 = User.objects.get(username="user 2")
        john = User.objects.get(username="johnsmith")
        users = [
                {"expanded_name":"", "id":user2.id, "small_name":user2.username, "string":user2.email},
                {"expanded_name":"", "id":john.id, "small_name":john.username, "string":john.email}
                ]
        users = str(users).replace("'", '"')
        data['users'] = users
        response, context = self.step_test(Booking_Meta, data)

    def test_step_with_bad_data(self):  # TODO
        data = {}
        response, context = self.step_test(Booking_Meta, data)

    def test_step_with_empty_data(self):
        data = {}
        response, context = self.step_test(Booking_Meta, data)


class DefineHardwareTestCase(BaseStepTestCase):

    def test_step_with_good_data(self):
        hosts = {"host_4": 1, "host_1": 1}
        labs = {"lab_1":"true"}
        data = {"hosts": hosts, "labs": labs}
        response, context = self.step_test(Define_Hardware, data)

    def test_step_with_bad_data(self):  # TODO
        data = {}
        response, context = self.step_test(Define_Hardware, data)

    def test_step_with_empty_data(self):
        data = {}
        response, context = self.step_test(Define_Hardware, data)


class HostMetaInfoTestCase(BaseStepTestCase):

    def makeRepo(self):
        """
        override to provide step with needed host info
        """
        repo = super(HostMetaInfoTestCase, self).makeRepo()
        # get models
        models = {}
        models['bundle'] = GenericResourceBundle()
        # make generic hosts
        gres1 = GenericResource(bundle=models['bundle'])
        prof1 = HostProfile.objects.get(name="Test profile 0")
        ghost1 = GenericHost(profile=prof1, resource=gres1)

        gres2 = GenericResource(bundle=models['bundle'])
        prof2 = HostProfile.objects.get(name="Test profile 3")
        ghost2 = GenericHost(profile=prof2, resource=gres2)
        models['hosts'] = [ghost1, ghost2]
        repo.el[repo.GRESOURCE_BUNDLE_MODELS] = models
        return repo

    def test_step_with_good_data(self):
        data = {"form-INITIAL_FORMS": 2, "form-MAX_NUM_FORMS": 1000}
        data["form-MIN_NUM_FORMS"] = 0
        data["form-TOTAL_FORMS"] = 2
        data['form-0-host_name'] = "first host"
        data['form-1-host_name'] = "second host"
        response, context = self.step_test(Host_Meta_Info, data)

    def test_step_with_bad_data(self):  # TODO
        data = {"form-INITIAL_FORMS": 0, "form-MAX_NUM_FORMS": 1000}
        data["form-MIN_NUM_FORMS"] = 0
        data["form-TOTAL_FORMS"] = 0
        response, context = self.step_test(Host_Meta_Info, data)

    def test_step_with_empty_data(self):
        data = {"form-INITIAL_FORMS": 0, "form-MAX_NUM_FORMS": 1000}
        data["form-MIN_NUM_FORMS"] = 0
        data["form-TOTAL_FORMS"] = 0
        response, context = self.step_test(Host_Meta_Info, data)


class DefineNetsTestCase(BaseStepTestCase):

    def test_step_with_good_data(self):
        xml = constants.POD_XML
        data = {"xml": xml}
        response, context = self.step_test(Define_Nets, data)

    def test_step_with_bad_data(self):  # TODO
        data = {}
        response, context = self.step_test(Define_Nets, data)

    def test_step_with_empty_data(self):
        data = {}
        response, context = self.step_test(Define_Nets, data)


class ResourceMetaInfoTestCase(BaseStepTestCase):

    def test_step_with_good_data(self):
        data = {"bundle_description": "description", "bundle_name": "my testing bundle"}
        response, context = self.step_test(Resource_Meta_Info, data)

    def test_step_with_bad_data(self):  # TODO
        data = {}
        response, context = self.step_test(Resource_Meta_Info, data)

    def test_step_with_empty_data(self):
        data = {}
        response, context = self.step_test(Resource_Meta_Info, data)


class SWConfResourceSelectTestCase(BaseStepTestCase):

    def test_step_with_good_data(self):
        grb_model = GenericResourceBundle.objects.filter(owner__username="user 1").first()
        grb = [{"small_name": grb_model.name, "expanded_name": "user 1", "id": grb_model.id, "string": ""}]
        grb = str(grb).replace("'", '"')
        data = {"generic_resource_bundle": grb }
        response, context = self.step_test(SWConf_Resource_Select, data)

    def test_step_with_bad_data(self):  # TODO
        data = {}
        response, context = self.step_test(SWConf_Resource_Select, data)

    def test_step_with_empty_data(self):
        data = {}
        response, context = self.step_test(SWConf_Resource_Select, data)


class DefineSoftwareTestCase(BaseStepTestCase):

    def makeRepo(self):
        """
        put selected grb in repo for step
        """
        repo = super(DefineSoftwareTestCase, self).makeRepo()
        grb = GenericResourceBundle.objects.filter(owner__username="user 1").first()
        repo.el[repo.SWCONF_SELECTED_GRB] = grb
        return repo


    def test_step_with_good_data(self):
        data = {"form-INITIAL_FORMS": 3, "form-MAX_NUM_FORMS": 1000}
        data["form-MIN_NUM_FORMS"] = 0
        data["form-TOTAL_FORMS"] = 3
        an_image_id = Image.objects.get(name="a host image").id
        another_image_id = Image.objects.get(name="another host image").id
        control = OPNFVRole.objects.get(name="Controller")
        compute = OPNFVRole.objects.get(name="Compute")
        jumphost = OPNFVRole.objects.get(name="Jumphost")
        data['form-0-image'] = an_image_id
        data['form-1-image'] = an_image_id
        data['form-2-image'] = another_image_id
        data['form-0-role'] = compute.id
        data['form-1-role'] = control.id
        data['form-2-role'] = jumphost.id
        response, context = self.step_test(Define_Software, data)

    def test_step_with_bad_data(self):  # TODO
        data = {"form-INITIAL_FORMS": 0, "form-MAX_NUM_FORMS": 1000}
        data["form-MIN_NUM_FORMS"] = 0
        data["form-TOTAL_FORMS"] = 0
        response, context = self.step_test(Define_Software, data)

    def test_step_with_empty_data(self):
        data = {"form-INITIAL_FORMS": 0, "form-MAX_NUM_FORMS": 1000}
        data["form-MIN_NUM_FORMS"] = 0
        data["form-TOTAL_FORMS"] = 0
        response, context = self.step_test(Define_Software, data)


class ConfigSoftwareTestCase(BaseStepTestCase):

    def test_step_with_good_data(self):
        data = {"description": "description", "name": "namey"}
        installer = Installer.objects.get(name="Fuel")
        scenario = Scenario.objects.get(name="os-nosdn-nofeature-noha")
        data['installer'] = installer.id
        data['scenario'] = scenario.id
        response, context = self.step_test(Config_Software, data)

    def test_step_with_bad_data(self):  # TODO
        data = {}
        response, context = self.step_test(Config_Software, data)

    def test_step_with_empty_data(self):
        data = {}
        response, context = self.step_test(Config_Software, data)

