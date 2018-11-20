##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.http import JsonResponse

import random

from booking.models import Booking
from workflow.workflow_factory import WorkflowFactory, MetaStep, MetaRelation
from workflow.models import Repository, Confirmation_Step
from resource_inventory.models import (
    GenericResourceBundle,
    ConfigBundle,
    HostConfiguration,
    OPNFVConfig
)

import logging
logger = logging.getLogger(__name__)


class SessionManager():

    def __init__(self, request=None):
        self.repository = Repository()
        self.repository.el[self.repository.SESSION_USER] = request.user
        self.repository.el['active_step'] = 0
        self.steps = []
        self.factory = WorkflowFactory()
        c_step = WorkflowFactory().make_step(Confirmation_Step, self.repository)
        self.steps.append(c_step)
        metaconfirm = MetaStep()
        metaconfirm.index = 0
        metaconfirm.short_title = "confirm"
        self.repository.el['steps'] = 1
        self.metaworkflow = None
        self.metaworkflows = []
        self.metarelations = []
        self.relationreverselookup = {}
        self.initialized = False
        self.active_index = 0
        self.step_meta = [metaconfirm]
        self.relation_depth = 0

    def add_workflow(self, workflow_type=None, target_id=None, **kwargs):
        if target_id is not None:
            self.prefill_repo(target_id, workflow_type)
        factory_steps, meta_info = self.factory.conjure(workflow_type=workflow_type, repo=self.repository)
        offset = len(meta_info)
        for relation in self.metarelations:
            if relation.depth > self.relation_depth:
                self.relation_depth = relation.depth
            if relation.parent >= self.repository.el['active_step']:
                relation.parent += offset
                for i in range(0, len(relation.children)):
                    if relation.children[i] >= self.repository.el['active_step']:
                        relation.children[i] += offset
        self.step_meta[self.active_index:self.active_index] = meta_info
        self.steps[self.active_index:self.active_index] = factory_steps

        if self.initialized:
            relation = MetaRelation()
            relation.parent = self.repository.el['active_step'] + offset
            relation.depth = self.relationreverselookup[self.step_meta[relation.parent]].depth + 1
            if relation.depth > self.relation_depth:
                self.relation_depth = relation.depth
            for i in range(self.repository.el['active_step'], offset + self.repository.el['active_step']):
                relation.children.append(i)
                self.relationreverselookup[self.step_meta[i]] = relation
            relation.color = "#%06x" % random.randint(0, 0xFFFFFF)
            self.metarelations.append(relation)
        else:
            relation = MetaRelation()
            relation.depth = 0
            relation.parent = 500000000000
            for i in range(0, len(self.step_meta)):
                relation.children.append(i)
                self.relationreverselookup[self.step_meta[i]] = relation
            self.metarelations.append(relation)
            self.initialized = True

    def status(self, request):
        try:
            steps = []
            for step in self.step_meta:
                steps.append(step.to_json())
            parents = {}
            children = {}
            responsejson = {}
            responsejson["steps"] = steps
            responsejson["active"] = self.repository.el['active_step']
            responsejson["relations"] = []
            i = 0
            for relation in self.metarelations:
                responsejson["relations"].append(relation.to_json())
                children[relation.parent] = i
                for child in relation.children:
                    parents[child] = i
                i += 1
            responsejson['max_depth'] = self.relation_depth
            responsejson['parents'] = parents
            responsejson['children'] = children
            return JsonResponse(responsejson, safe=False)
        except Exception:
            pass

    def render(self, request, **kwargs):
        # filter out when a step needs to handle post/form data
        # if 'workflow' in post data, this post request was meant for me, not step
        if request.method == 'POST' and request.POST.get('workflow', None) is None:
            return self.steps[self.active_index].post_render(request)
        return self.steps[self.active_index].render(request)

    def post_render(self, request):
        return self.steps[self.active_index].post_render(request)

    def goto(self, num, **kwargs):
        self.repository.el['active_step'] = int(num)
        self.active_index = int(num)
        # TODO: change to include some checking

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
        self.repository.el[self.repository.BOOKING_MODELS] = models
        self.repository.el[self.repository.CONFIRMATION] = confirmation
        self.repository.el[self.repository.GRESOURCE_BUNDLE_MODELS] = self.make_grb_models(booking.resource.template)
        self.repository.el[self.repository.BOOKING_SELECTED_GRB] = self.make_grb_models(booking.resource.template)['bundle']
        self.repository.el[self.repository.CONFIG_MODELS] = self.make_config_models(booking.config_bundle)

    def prefill_resource(self, resource):
        models = self.make_grb_models(resource)
        confirm = self.make_grb_confirm(resource)
        self.repository.el[self.repository.GRESOURCE_BUNDLE_MODELS] = models
        self.repository.el[self.repository.CONFIRMATION] = confirm

    def prefill_config(self, config):
        models = self.make_config_models(config)
        confirm = self.make_config_confirm(config)
        self.repository.el[self.repository.CONFIG_MODELS] = models
        self.repository.el[self.repository.CONFIRMATION] = confirm
        grb_models = self.make_grb_models(config.bundle)
        self.repository.el[self.repository.GRESOURCE_BUNDLE_MODELS] = grb_models
        self.repository.el[self.repository.SWCONF_SELECTED_GRB] = config.bundle

    def make_grb_models(self, resource):
        models = self.repository.el.get(self.repository.GRESOURCE_BUNDLE_MODELS, {})
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
        confirm = self.repository.el.get(self.repository.CONFIRMATION, {})
        confirm['resource'] = {}
        confirm['resource']['hosts'] = []
        confirm['resource']['lab'] = resource.lab.lab_user.username
        for host in resource.getHosts():
            confirm['resource']['hosts'].append({"name": host.resource.name, "profile": host.profile.name})
        return confirm

    def make_config_models(self, config):
        models = self.repository.el.get(self.repository.CONFIG_MODELS, {})
        models['bundle'] = config
        models['host_configs'] = []
        for host_conf in HostConfiguration.objects.filter(bundle=config):
            models['host_configs'].append(host_conf)
        models['opnfv'] = OPNFVConfig.objects.filter(bundle=config).last()
        return models

    def make_config_confirm(self, config):
        confirm = self.repository.el.get(self.repository.CONFIRMATION, {})
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
        models = self.repository.el.get(self.repository.BOOKING_MODELS, {})
        models['booking'] = booking
        models['collaborators'] = []
        for user in booking.collaborators.all():
            models['collaborators'].append(user)
        return models

    def make_booking_confirm(self, booking):
        confirm = self.repository.el.get(self.repository.CONFIRMATION, {})
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
