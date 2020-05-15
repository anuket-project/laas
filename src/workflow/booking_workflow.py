##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.utils import timezone

from datetime import timedelta

from booking.models import Booking
from workflow.models import WorkflowStep, AbstractSelectOrCreate
from workflow.forms import ResourceSelectorForm, SWConfigSelectorForm, BookingMetaForm, OPNFVSelectForm
from resource_inventory.models import OPNFVConfig, ResourceTemplate
from django.db.models import Q


"""
subclassing notes:
    subclasses have to define the following class attributes:
        self.repo_key: main output of step, where the selected/created single selector
            result is placed at the end
        self.confirm_key:
"""


class Abstract_Resource_Select(AbstractSelectOrCreate):
    form = ResourceSelectorForm
    template = 'dashboard/genericselect.html'
    title = "Select Resource"
    description = "Select a resource template to use for your deployment"
    short_title = "pod select"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.select_repo_key = self.repo.SELECTED_RESOURCE_TEMPLATE
        self.confirm_key = self.workflow_type

    def alert_bundle_missing(self):
        self.set_invalid("Please select a valid resource template")

    def get_form_queryset(self):
        user = self.repo_get(self.repo.SESSION_USER)
        return ResourceTemplate.objects.filter((Q(owner=user) | Q(public=True)))

    def get_page_context(self):
        return {
            'select_type': 'resource',
            'select_type_title': 'Resource template',
            'addable_type_num': 1
        }

    def put_confirm_info(self, bundle):
        confirm_dict = self.repo_get(self.repo.CONFIRMATION)
        if self.confirm_key not in confirm_dict:
            confirm_dict[self.confirm_key] = {}
        confirm_dict[self.confirm_key]["Resource Template"] = bundle.name
        self.repo_put(self.repo.CONFIRMATION, confirm_dict)


class Booking_Resource_Select(Abstract_Resource_Select):
    workflow_type = "booking"


class SWConfig_Select(AbstractSelectOrCreate):
    title = "Select Software Configuration"
    description = "Choose the software and related configurations you want to have used for your deployment"
    short_title = "pod config"
    form = SWConfigSelectorForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.select_repo_key = self.repo.SELECTED_CONFIG_BUNDLE
        self.confirm_key = "booking"

    def alert_bundle_missing(self):
        self.set_invalid("Please select a valid pod config")

    def get_form_queryset(self):
        user = self.repo_get(self.repo.SESSION_USER)
        grb = self.repo_get(self.repo.SELECTED_RESOURCE_TEMPLATE)
        qs = ResourceTemplate.objects.filter(Q(hidden=False) & (Q(owner=user) | Q(public=True))).filter(bundle=grb)
        return qs

    def put_confirm_info(self, bundle):
        confirm_dict = self.repo_get(self.repo.CONFIRMATION)
        if self.confirm_key not in confirm_dict:
            confirm_dict[self.confirm_key] = {}
        confirm_dict[self.confirm_key]["Software Configuration"] = bundle.name
        self.repo_put(self.repo.CONFIRMATION, confirm_dict)

    def get_page_context(self):
        return {
            'select_type': 'swconfig',
            'select_type_title': 'Software Config',
            'addable_type_num': 2
        }


class OPNFV_EnablePicker(object):
    pass


class OPNFV_Select(AbstractSelectOrCreate, OPNFV_EnablePicker):
    title = "Choose an OPNFV Config"
    description = "Choose or create a description of how you want to deploy OPNFV"
    short_title = "opnfv config"
    form = OPNFVSelectForm
    enabled = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.select_repo_key = self.repo.SELECTED_OPNFV_CONFIG
        self.confirm_key = "booking"

    def alert_bundle_missing(self):
        self.set_invalid("Please select a valid OPNFV config")

    def get_form_queryset(self):
        cb = self.repo_get(self.repo.SELECTED_CONFIG_BUNDLE)
        qs = OPNFVConfig.objects.filter(bundle=cb)
        return qs

    def put_confirm_info(self, config):
        confirm_dict = self.repo_get(self.repo.CONFIRMATION)
        if self.confirm_key not in confirm_dict:
            confirm_dict[self.confirm_key] = {}
        confirm_dict[self.confirm_key]["OPNFV Configuration"] = config.name
        self.repo_put(self.repo.CONFIRMATION, confirm_dict)

    def get_page_context(self):
        return {
            'select_type': 'opnfv',
            'select_type_title': 'OPNFV Config',
            'addable_type_num': 4
        }


class Booking_Meta(WorkflowStep):
    template = 'booking/steps/booking_meta.html'
    title = "Extra Info"
    description = "Tell us how long you want your booking, what it is for, and who else should have access to it"
    short_title = "booking info"

    def get_context(self):
        context = super(Booking_Meta, self).get_context()
        initial = {}
        default = []
        try:
            models = self.repo_get(self.repo.BOOKING_MODELS, {})
            booking = models.get("booking")
            if booking:
                initial['purpose'] = booking.purpose
                initial['project'] = booking.project
                initial['length'] = (booking.end - booking.start).days
            info = self.repo_get(self.repo.BOOKING_INFO_FILE, False)
            if info:
                initial['info_file'] = info
            users = models.get("collaborators", [])
            for user in users:
                default.append(user.userprofile)
        except Exception:
            pass

        owner = self.repo_get(self.repo.SESSION_USER)

        context['form'] = BookingMetaForm(initial=initial, user_initial=default, owner=owner)
        return context

    def post(self, post_data, user):
        form = BookingMetaForm(data=post_data, owner=user)

        forms = self.repo_get(self.repo.BOOKING_FORMS, {})

        forms["meta_form"] = form
        self.repo_put(self.repo.BOOKING_FORMS, forms)

        if form.is_valid():
            models = self.repo_get(self.repo.BOOKING_MODELS, {})
            if "booking" not in models:
                models['booking'] = Booking()
            models['collaborators'] = []
            confirm = self.repo_get(self.repo.CONFIRMATION)
            if "booking" not in confirm:
                confirm['booking'] = {}

            models['booking'].start = timezone.now()
            models['booking'].end = timezone.now() + timedelta(days=int(form.cleaned_data['length']))
            models['booking'].purpose = form.cleaned_data['purpose']
            models['booking'].project = form.cleaned_data['project']
            for key in ['length', 'project', 'purpose']:
                confirm['booking'][key] = form.cleaned_data[key]

            if form.cleaned_data["deploy_opnfv"]:
                self.repo_get(self.repo.SESSION_MANAGER).set_step_statuses(OPNFV_EnablePicker, desired_enabled=True)
            else:
                self.repo_get(self.repo.SESSION_MANAGER).set_step_statuses(OPNFV_EnablePicker, desired_enabled=False)

            userprofile_list = form.cleaned_data['users']
            confirm['booking']['collaborators'] = []
            for userprofile in userprofile_list:
                models['collaborators'].append(userprofile.user)
                confirm['booking']['collaborators'].append(userprofile.user.username)

            info_file = form.cleaned_data.get("info_file", False)
            if info_file:
                self.repo_put(self.repo.BOOKING_INFO_FILE, info_file)

            self.repo_put(self.repo.BOOKING_MODELS, models)
            self.repo_put(self.repo.CONFIRMATION, confirm)
            self.set_valid("Step Completed")
        else:
            self.set_invalid("Please complete the fields highlighted in red to continue")
