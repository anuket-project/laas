##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.http import JsonResponse

from booking.models import Booking
from workflow.workflow_factory import WorkflowFactory
from workflow.models import Repository
from resource_inventory.models import (
    GenericResourceBundle,
    ConfigBundle,
    HostConfiguration,
    OPNFVConfig
)

import logging
logger = logging.getLogger(__name__)


class SessionManager():
    def active_workflow(self):
        return self.workflows[-1]

    def __init__(self, request=None):
        self.workflows = []

        self.owner = request.user

        self.factory = WorkflowFactory()

    def set_step_statuses(self, superclass_type, desired_enabled=True):
        workflow = self.active_workflow()
        steps = workflow.steps
        for step in steps:
            if isinstance(step, superclass_type):
                if desired_enabled:
                    step.enable()
                else:
                    step.disable()

    def add_workflow(self, workflow_type=None, target_id=None, **kwargs):
        if target_id is not None:
            self.prefill_repo(target_id, workflow_type)

        repo = Repository()
        if(len(self.workflows) >= 1):
            defaults = self.workflows[-1].repository.get_child_defaults()
            repo.set_defaults(defaults)
            repo.el[repo.HAS_RESULT] = False
        repo.el[repo.SESSION_USER] = self.owner
        repo.el[repo.SESSION_MANAGER] = self
        self.workflows.append(
            self.factory.create_workflow(
                workflow_type=workflow_type,
                repo=repo
            )
        )

    def pop_workflow(self):
        if(len(self.workflows) <= 1):
            return False

        if self.workflows[-1].repository.el[self.workflows[-1].repository.HAS_RESULT]:
            key = self.workflows[-1].repository.el[self.workflows[-1].repository.RESULT_KEY]
            result = self.workflows[-1].repository.el[self.workflows[-1].repository.RESULT]
            self.workflows[-2].repository.el[key] = result
        self.workflows.pop()
        return True

    def status(self, request):
        try:
            meta_json = []
            for step in self.active_workflow().steps:
                meta_json.append(step.to_json())
            responsejson = {}
            responsejson["steps"] = meta_json
            responsejson["active"] = self.active_workflow().repository.el['active_step']
            responsejson["workflow_count"] = len(self.workflows)
            return JsonResponse(responsejson, safe=False)
        except Exception:
            pass

    def render(self, request, **kwargs):
        # filter out when a step needs to handle post/form data
        # if 'workflow' in post data, this post request was meant for me, not step
        if request.method == 'POST' and request.POST.get('workflow', None) is None:
            return self.active_workflow().steps[self.active_workflow().active_index].post_render(request)
        return self.active_workflow().steps[self.active_workflow().active_index].render(request)

    def post_render(self, request):
        return self.active_workflow().steps[self.active_workflow().active_index].post_render(request)

    def go_next(self, **kwargs):
        next_step = self.active_workflow().active_index + 1
        if next_step >= len(self.active_workflow().steps):
            raise Exception("Out of bounds request for step")
        while not self.active_workflow().steps[next_step].enabled:
            next_step += 1
        self.active_workflow().repository.el['active_step'] = next_step
        self.active_workflow().active_index = next_step

    def go_prev(self, **kwargs):
        prev_step = self.active_workflow().active_index - 1
        if prev_step < 0:
            raise Exception("Out of bounds request for step")
        while not self.active_workflow().steps[prev_step].enabled:
            prev_step -= 1
        self.active_workflow().repository.el['active_step'] = prev_step
        self.active_workflow().active_index = prev_step

    def prefill_repo(self, target_id, workflow_type):
        self.repository.el[self.repository.EDIT] = True
        edit_object = None
        if workflow_type == 0:
            edit_object = Booking.objects.get(pk=target_id)
            self.prefill_booking(edit_object)
        elif workflow_type == 1:
            edit_object = GenericResourceBundle.objects.get(pk=target_id)
            self.prefill_resource(edit_object)
        elif workflow_type == 2:
            edit_object = ConfigBundle.objects.get(pk=target_id)
            self.prefill_config(edit_object)

    def prefill_booking(self, booking):
        models = self.make_booking_models(booking)
        confirmation = self.make_booking_confirm(booking)
        self.active_workflow().repository.el[self.active_workflow().repository.BOOKING_MODELS] = models
        self.active_workflow().repository.el[self.active_workflow().repository.CONFIRMATION] = confirmation
        self.active_workflow().repository.el[self.active_workflow().repository.GRESOURCE_BUNDLE_MODELS] = self.make_grb_models(booking.resource.template)
        self.active_workflow().repository.el[self.active_workflow().repository.SELECTED_GRESOURCE_BUNDLE] = self.make_grb_models(booking.resource.template)['bundle']
        self.active_workflow().repository.el[self.active_workflow().repository.CONFIG_MODELS] = self.make_config_models(booking.config_bundle)

    def prefill_resource(self, resource):
        models = self.make_grb_models(resource)
        confirm = self.make_grb_confirm(resource)
        self.active_workflow().repository.el[self.active_workflow().repository.GRESOURCE_BUNDLE_MODELS] = models
        self.active_workflow().repository.el[self.active_workflow().repository.CONFIRMATION] = confirm

    def prefill_config(self, config):
        models = self.make_config_models(config)
        confirm = self.make_config_confirm(config)
        self.active_workflow().repository.el[self.active_workflow().repository.CONFIG_MODELS] = models
        self.active_workflow().repository.el[self.active_workflow().repository.CONFIRMATION] = confirm
        grb_models = self.make_grb_models(config.bundle)
        self.active_workflow().repository.el[self.active_workflow().repository.GRESOURCE_BUNDLE_MODELS] = grb_models

    def make_grb_models(self, resource):
        models = self.active_workflow().repository.el.get(self.active_workflow().repository.GRESOURCE_BUNDLE_MODELS, {})
        models['hosts'] = []
        models['bundle'] = resource
        models['interfaces'] = {}
        models['vlans'] = {}
        for host in resource.getHosts():
            models['hosts'].append(host)
            models['interfaces'][host.resource.name] = []
            models['vlans'][host.resource.name] = {}
            for interface in host.generic_interfaces.all():
                models['interfaces'][host.resource.name].append(interface)
                models['vlans'][host.resource.name][interface.profile.name] = []
                for vlan in interface.vlans.all():
                    models['vlans'][host.resource.name][interface.profile.name].append(vlan)
        return models

    def make_grb_confirm(self, resource):
        confirm = self.active_workflow().repository.el.get(self.active_workflow().repository.CONFIRMATION, {})
        confirm['resource'] = {}
        confirm['resource']['hosts'] = []
        confirm['resource']['lab'] = resource.lab.lab_user.username
        for host in resource.getHosts():
            confirm['resource']['hosts'].append({"name": host.resource.name, "profile": host.profile.name})
        return confirm

    def make_config_models(self, config):
        models = self.active_workflow().repository.el.get(self.active_workflow().repository.CONFIG_MODELS, {})
        models['bundle'] = config
        models['host_configs'] = []
        for host_conf in HostConfiguration.objects.filter(bundle=config):
            models['host_configs'].append(host_conf)
        models['opnfv'] = OPNFVConfig.objects.filter(bundle=config).last()
        return models

    def make_config_confirm(self, config):
        confirm = self.active_workflow().repository.el.get(self.active_workflow().repository.CONFIRMATION, {})
        confirm['configuration'] = {}
        confirm['configuration']['hosts'] = []
        confirm['configuration']['name'] = config.name
        confirm['configuration']['description'] = config.description
        opnfv = OPNFVConfig.objects.filter(bundle=config).last()
        confirm['configuration']['installer'] = opnfv.installer.name
        confirm['configuration']['scenario'] = opnfv.scenario.name
        for host_conf in HostConfiguration.objects.filter(bundle=config):
            h = {"name": host_conf.host.resource.name, "image": host_conf.image.name, "role": host_conf.opnfvRole.name}
            confirm['configuration']['hosts'].append(h)
        return confirm

    def make_booking_models(self, booking):
        models = self.active_workflow().repository.el.get(self.active_workflow().repository.BOOKING_MODELS, {})
        models['booking'] = booking
        models['collaborators'] = []
        for user in booking.collaborators.all():
            models['collaborators'].append(user)
        return models

    def make_booking_confirm(self, booking):
        confirm = self.active_workflow().repository.el.get(self.active_workflow().repository.CONFIRMATION, {})
        confirm['booking'] = {}
        confirm['booking']['length'] = (booking.end - booking.start).days
        confirm['booking']['project'] = booking.project
        confirm['booking']['purpose'] = booking.purpose
        confirm['booking']['resource name'] = booking.resource.template.name
        confirm['booking']['configuration name'] = booking.config_bundle.name
        confirm['booking']['collaborators'] = []
        for user in booking.collaborators.all():
            confirm['booking']['collaborators'].append(user.username)
        return confirm


class ManagerTracker():
    instance = None

    managers = {}

    def __init__(self):
        pass

    @staticmethod
    def getInstance():
        if ManagerTracker.instance is None:
            ManagerTracker.instance = ManagerTracker()
        return ManagerTracker.instance
