##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from workflow.booking_workflow import *
from workflow.resource_bundle_workflow import *
from workflow.sw_bundle_workflow import *
from workflow.snapshot_workflow import *
from workflow.models import Workflow, Repository

import uuid

import logging
logger = logging.getLogger(__name__)

class BookingMetaWorkflow(object):
    workflow_type = 0
    color = "#0099ff"
    is_child = False

class ResourceMetaWorkflow(object):
    workflow_type = 1
    color = "#ff6600"

class ConfigMetaWorkflow(object):
    workflow_type = 2
    color = "#00ffcc"

class MetaRelation(object):
    def __init__(self, *args, **kwargs):
        self.color = "#cccccc"
        self.parent = 0
        self.children = []
        self.depth = -1

    def to_json(self):
        return {
            'color': self.color,
            'parent': self.parent,
            'children': self.children,
            'depth': self.depth,
        }

class MetaStep(object):
    #valid = 0 #0 is not checked, 1 is invalid, 2 is valid

    UNTOUCHED = 0
    INVALID = 100
    VALID = 200

    def set_invalid(self, message, code=100):
        self.valid = code
        self.message = message

    def set_valid(self, message, code=200):
        self.valid = code
        self.message = message

    def __init__(self, *args, **kwargs):
        self.short_title = "error"
        self.skip_step = 0
        self.valid = 0
        self.message = ""
        self.id = uuid.uuid4()

    def to_json(self):
        return {
            'title': self.short_title,
            'skip': self.skip_step,
            'valid': self.valid,
            'message': self.message,
        }

    def __str__(self):
        return "metastep: " + str(self.short_title)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id.int == other.id.int

    def __ne__(self, other):
        return self.id.int != other.id.int

class WorkflowFactory():
    #def __init__(self, *args, **kwargs):
    booking_steps = [
            Booking_Resource_Select,
            SWConfig_Select,
            Booking_Meta
        ]

    resource_steps = [
            Define_Hardware,
            Define_Nets,
            Resource_Meta_Info,
        ]

    config_steps = [
            SWConf_Resource_Select,
            Define_Software,
            Config_Software,
        ]

    snapshot_steps = [
            Select_Host_Step,
            Image_Meta_Step
        ]

    def conjure(self, workflow_type=None, repo=None):
        workflow_types = [
                self.booking_steps,
                self.resource_steps,
                self.config_steps,
                self.snapshot_steps,
        ]

        steps = self.make_steps(workflow_types[workflow_type], repository=repo)
        meta_steps = self.metaize(steps=steps, wf_type=workflow_type)
        return steps, meta_steps

    def make_steps(self, step_types, repository):
        repository.el['steps'] += len(step_types)
        steps = []
        for step_type in step_types:
            steps.append(self.make_step(step_type, repository))

        return steps

    def make_step(self, step_type, repository):
        iden = step_type.description + step_type.title + step_type.template
        return step_type(iden, repository)

    def metaize(self, steps, wf_type):
        meta_dict = []
        for step in steps:
            meta_step = MetaStep()
            meta_step.short_title = step.short_title
            meta_dict.append(meta_step)
            step.metastep = meta_step

        return meta_dict
