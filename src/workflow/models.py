##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.template.loader import get_template
from django.http import HttpResponse
from django.utils import timezone
from django.db import transaction

import yaml
import requests

from workflow.forms import ConfirmationForm
from api.models import JobFactory
from dashboard.exceptions import ResourceAvailabilityException, ModelValidationException
from resource_inventory.models import Image, OPNFVConfig, ResourceOPNFVConfig, NetworkRole
from resource_inventory.resource_manager import ResourceManager
from resource_inventory.pdf_templater import PDFTemplater
from notifier.manager import NotificationHandler
from booking.models import Booking


class BookingAuthManager():
    """
    Verifies Booking Authorization.

    Class to verify that the user is allowed to book the requested resource
    The user must input a url to the INFO.yaml file to prove that they are the ptl of
    an approved project if they are booking a multi-node pod.
    This class parses the url and checks the logged in user against the info file.
    """

    LFN_PROJECTS = ["opnfv"]  # TODO

    def parse_github_url(self, url):
        project_leads = []
        try:
            parts = url.split("/")
            if "http" in parts[0]:  # the url include http(s)://
                parts = parts[2:]
            if parts[-1] != "INFO.yaml":
                return None
            if parts[0] not in ["github.com", "raw.githubusercontent.com"]:
                return None
            if parts[1] not in self.LFN_PROJECTS:
                return None
            # now to download and parse file
            if parts[3] == "blob":
                parts[3] = "raw"
            url = "https://" + "/".join(parts)
            info_file = requests.get(url, timeout=15).text
            info_parsed = yaml.load(info_file)
            ptl = info_parsed.get('project_lead')
            if ptl:
                project_leads.append(ptl)
            sub_ptl = info_parsed.get("subproject_lead")
            if sub_ptl:
                project_leads.append(sub_ptl)

        except Exception:
            pass

        return project_leads

    def parse_gerrit_url(self, url):
        project_leads = []
        try:
            halfs = url.split("?")
            parts = halfs[0].split("/")
            args = halfs[1].split(";")
            if "http" in parts[0]:  # the url include http(s)://
                parts = parts[2:]
            if "f=INFO.yaml" not in args:
                return None
            if "gerrit.opnfv.org" not in parts[0]:
                return None
            try:
                i = args.index("a=blob")
                args[i] = "a=blob_plain"
            except ValueError:
                pass
            # recreate url
            halfs[1] = ";".join(args)
            halfs[0] = "/".join(parts)
            # now to download and parse file
            url = "https://" + "?".join(halfs)
            info_file = requests.get(url, timeout=15).text
            info_parsed = yaml.load(info_file)
            ptl = info_parsed.get('project_lead')
            if ptl:
                project_leads.append(ptl)
            sub_ptl = info_parsed.get("subproject_lead")
            if sub_ptl:
                project_leads.append(sub_ptl)

        except Exception:
            return None

        return project_leads

    def parse_opnfv_git_url(self, url):
        project_leads = []
        try:
            parts = url.split("/")
            if "http" in parts[0]:  # the url include http(s)://
                parts = parts[2:]
            if "INFO.yaml" not in parts[-1]:
                return None
            if "git.opnfv.org" not in parts[0]:
                return None
            if parts[-2] == "tree":
                parts[-2] = "plain"
            # now to download and parse file
            url = "https://" + "/".join(parts)
            info_file = requests.get(url, timeout=15).text
            info_parsed = yaml.load(info_file)
            ptl = info_parsed.get('project_lead')
            if ptl:
                project_leads.append(ptl)
            sub_ptl = info_parsed.get("subproject_lead")
            if sub_ptl:
                project_leads.append(sub_ptl)

        except Exception:
            return None

        return project_leads

    def parse_url(self, info_url):
        """
        Parse the project URL.

        Gets the INFO.yaml file from the project and returns the PTL info.
        """
        if "github" in info_url:
            return self.parse_github_url(info_url)

        if "gerrit.opnfv.org" in info_url:
            return self.parse_gerrit_url(info_url)

        if "git.opnfv.org" in info_url:
            return self.parse_opnfv_git_url(info_url)

    def booking_allowed(self, booking, repo):
        """
        Assert the current Booking Policy.

        This is the method that will have to change whenever the booking policy changes in the Infra
        group / LFN. This is a nice isolation of that administration crap
        currently checks if the booking uses multiple servers. if it does, then the owner must be a PTL,
        which is checked using the provided info file
        """
        if booking.owner.userprofile.booking_privledge:
            return True  # admin override for this user
        if Booking.objects.filter(owner=booking.owner, end__gt=timezone.now()).count() >= 3:
            return False
        if len(booking.resource.template.get_required_resources()) < 2:
            return True  # if they only have one server, we dont care
        if repo.BOOKING_INFO_FILE not in repo.el:
            return False  # INFO file not provided
        ptl_info = self.parse_url(repo.el.get(repo.BOOKING_INFO_FILE))
        for ptl in ptl_info:
            if ptl['email'] == booking.owner.userprofile.email_addr:
                return True
        return False


class WorkflowStepStatus(object):
    """
    Poor man's enum for the status of a workflow step.

    The steps in a workflow are not completed (UNTOUCHED)
    or they have been completed correctly (VALID) or they were filled out
    incorrectly (INVALID)
    """

    UNTOUCHED = 0
    INVALID = 100
    VALID = 200


class WorkflowStep(object):
    template = 'bad_request.html'
    title = "Generic Step"
    description = "You were led here by mistake"
    short_title = "error"
    metastep = None
    # phasing out metastep:

    valid = WorkflowStepStatus.UNTOUCHED
    message = ""

    enabled = True

    def cleanup(self):
        raise Exception("WorkflowStep subclass of type " + str(type(self)) + " has no concrete implemented cleanup() method")

    def enable(self):
        if not self.enabled:
            self.enabled = True

    def disable(self):
        if self.enabled:
            self.cleanup()
            self.enabled = False

    def set_invalid(self, message, code=WorkflowStepStatus.INVALID):
        self.valid = code
        self.message = message

    def set_valid(self, message, code=WorkflowStepStatus.VALID):
        self.valid = code
        self.message = message

    def to_json(self):
        return {
            'title': self.short_title,
            'enabled': self.enabled,
            'valid': self.valid,
            'message': self.message,
        }

    def __init__(self, id, repo=None):
        self.repo = repo
        self.id = id

    def get_context(self):
        context = {}
        context['step_number'] = self.repo_get('steps')
        context['active_step'] = self.repo_get('active_step')
        context['render_correct'] = "true"
        context['step_title'] = self.title
        context['description'] = self.description
        return context

    def render(self, request):
        return HttpResponse(self.render_to_string(request))

    def render_to_string(self, request):
        template = get_template(self.template)
        return template.render(self.get_context(), request)

    def post(self, post_content, user):
        raise Exception("WorkflowStep subclass of type " + str(type(self)) + " has no concrete post() method")

    def validate(self, request):
        pass

    def repo_get(self, key, default=None):
        return self.repo.get(key, default, self.id)

    def repo_put(self, key, value):
        return self.repo.put(key, value, self.id)


"""
subclassing notes:
    subclasses have to define the following class attributes:
        self.select_repo_key: where the selected "object" or "bundle" is to be placed in the repo
        self.form: the form to be used
        alert_bundle_missing(): what message to display if a user does not select/selects an invalid object
        get_form_queryset(): generate a queryset to be used to filter available items for the field
        get_page_context(): return simple context such as page header and other info
"""


class AbstractSelectOrCreate(WorkflowStep):
    template = 'dashboard/genericselect.html'
    title = "Select a Bundle"
    short_title = "select"
    description = "Generic bundle selector step"

    select_repo_key = None
    form = None  # subclasses are expected to use a form that is a subclass of SearchableSelectGenericForm

    def alert_bundle_missing(self):  # override in subclasses to change message if field isn't filled out
        self.set_invalid("Please select a valid bundle")

    def post(self, post_data, user):
        form = self.form(post_data, queryset=self.get_form_queryset())
        if form.is_valid():
            bundle = form.get_validated_bundle()
            if not bundle:
                self.alert_bundle_missing()
                return
            self.repo_put(self.select_repo_key, bundle)
            self.put_confirm_info(bundle)
            self.set_valid("Step Completed")
        else:
            self.alert_bundle_missing()

    def get_context(self):
        default = []

        bundle = self.repo_get(self.select_repo_key, False)
        if bundle:
            default.append(bundle)

        form = self.form(queryset=self.get_form_queryset(), initial=default)

        context = {'form': form, **self.get_page_context()}
        context.update(super().get_context())

        return context

    def get_page_context():
        return {
            'select_type': 'generic',
            'select_type_title': 'Generic Bundle'
        }


class Confirmation_Step(WorkflowStep):
    template = 'workflow/confirm.html'
    title = "Confirm Changes"
    description = "Does this all look right?"

    short_title = "confirm"

    def get_context(self):
        context = super(Confirmation_Step, self).get_context()
        context['form'] = ConfirmationForm()
        # Summary of submitted form data shown on the 'confirm' step of the workflow
        confirm_details = "\nPod:\n  Name: '{name}'\n  Description: '{desc}'\nLab: '{lab}'".format(
            name=self.repo_get(self.repo.CONFIRMATION)['resource']['name'],
            desc=self.repo_get(self.repo.CONFIRMATION)['resource']['description'],
            lab=self.repo_get(self.repo.CONFIRMATION)['template']['lab'])
        confirm_details += "\nResources:"
        for i, device in enumerate(self.repo_get(self.repo.RESOURCE_TEMPLATE_MODELS)['resources']):
            confirm_details += "\n  " + str(device) + ": " + str(self.repo_get(self.repo.CONFIRMATION)['template']['resources'][i]['profile'])
        context['confirmation_info'] = confirm_details
        if self.valid == WorkflowStepStatus.VALID:
            context["confirm_succeeded"] = "true"

        return context

    def flush_to_db(self):
        errors = self.repo.make_models()
        if errors:
            return errors

    def post(self, post_data, user):
        form = ConfirmationForm(post_data)
        if form.is_valid():
            data = form.cleaned_data['confirm']
            if data == "True":
                errors = self.flush_to_db()
                if errors:
                    self.set_invalid("ERROR OCCURRED: " + errors)
                else:
                    self.set_valid("Confirmed")

            elif data == "False":
                self.repo.cancel()
                self.set_valid("Canceled")
            else:
                self.set_invalid("Bad Form Contents")

        else:
            self.set_invalid("Bad Form Contents")


class Repository():

    EDIT = "editing"
    MODELS = "models"
    RESOURCE_SELECT = "resource_select"
    CONFIRMATION = "confirmation"
    SELECTED_RESOURCE_TEMPLATE = "selected resource template pk"
    SELECTED_OPNFV_CONFIG = "selected opnfv deployment config"
    RESOURCE_TEMPLATE_MODELS = "generic_resource_template_models"
    RESOURCE_TEMPLATE_INFO = "generic_resource_template_info"
    BOOKING = "booking"
    LAB = "lab"
    RCONFIG_LAST_HOSTLIST = "resource_configuration_network_previous_hostlist"
    BOOKING_FORMS = "booking_forms"
    SWCONF_HOSTS = "swconf_hosts"
    BOOKING_MODELS = "booking models"
    CONFIG_MODELS = "configuration bundle models"
    OPNFV_MODELS = "opnfv configuration models"
    SESSION_USER = "session owner user account"
    SESSION_MANAGER = "session manager for current session"
    VALIDATED_MODEL_GRB = "valid grb config model instance in db"
    VALIDATED_MODEL_CONFIG = "valid config model instance in db"
    VALIDATED_MODEL_BOOKING = "valid booking model instance in db"
    VLANS = "a list of vlans"
    SNAPSHOT_MODELS = "the models for snapshotting"
    SNAPSHOT_BOOKING_ID = "the booking id for snapshotting"
    SNAPSHOT_NAME = "the name of the snapshot"
    SNAPSHOT_DESC = "description of the snapshot"
    BOOKING_INFO_FILE = "the INFO.yaml file for this user's booking"

    # new keys for migration to using ResourceTemplates:
    RESOURCE_TEMPLATE_MODELS = "current working model of resource template"

    # migratory elements of segmented workflow
    # each of these is the end result of a different workflow.
    HAS_RESULT = "whether or not workflow has a result"
    RESULT_KEY = "key for target index that result will be put into in parent"
    RESULT = "result object from workflow"

    def get_child_defaults(self):
        return_tuples = []
        for key in [self.SELECTED_RESOURCE_TEMPLATE, self.SESSION_USER]:
            return_tuples.append((key, self.el.get(key)))
        return return_tuples

    def set_defaults(self, defaults):
        for key, value in defaults:
            self.el[key] = value

    def get(self, key, default, id):

        self.add_get_history(key, id)
        return self.el.get(key, default)

    def put(self, key, val, id):
        self.add_put_history(key, id)
        self.el[key] = val

    def add_get_history(self, key, id):
        self.add_history(key, id, self.get_history)

    def add_put_history(self, key, id):
        self.add_history(key, id, self.put_history)

    def add_history(self, key, id, history):
        if key not in history:
            history[key] = [id]
        else:
            history[key].append(id)

    def cancel(self):
        if self.RESOURCE_TEMPLATE_MODELS in self.el:
            models = self.el[self.RESOURCE_TEMPLATE_MODELS]
            if models['template'].temporary:
                models['template'].delete()
                # deleting current template should cascade delete all
                # necessary related models

    def make_models(self):
        if self.SNAPSHOT_MODELS in self.el:
            errors = self.make_snapshot()
            if errors:
                return errors

        # if GRB WF, create it
        if self.RESOURCE_TEMPLATE_MODELS in self.el:
            errors = self.make_generic_resource_bundle()
            if errors:
                return errors
            else:
                self.el[self.HAS_RESULT] = True
                self.el[self.RESULT_KEY] = self.SELECTED_RESOURCE_TEMPLATE
                return

        if self.OPNFV_MODELS in self.el:
            errors = self.make_opnfv_config()
            if errors:
                return errors
            else:
                self.el[self.HAS_RESULT] = True
                self.el[self.RESULT_KEY] = self.SELECTED_OPNFV_CONFIG

        if self.BOOKING_MODELS in self.el:
            errors = self.make_booking()
            if errors:
                return errors
            # create notification
            booking = self.el[self.BOOKING_MODELS]['booking']
            NotificationHandler.notify_new_booking(booking)

    def make_snapshot(self):
        owner = self.el[self.SESSION_USER]
        models = self.el[self.SNAPSHOT_MODELS]
        image = models.get('snapshot', Image())
        booking_id = self.el.get(self.SNAPSHOT_BOOKING_ID)
        if not booking_id:
            return "SNAP, No booking ID provided"
        booking = Booking.objects.get(pk=booking_id)
        if booking.start > timezone.now() or booking.end < timezone.now():
            return "Booking is not active"
        name = self.el.get(self.SNAPSHOT_NAME)
        if not name:
            return "SNAP, no name provided"
        host = models.get('host')
        if not host:
            return "SNAP, no host provided"
        description = self.el.get(self.SNAPSHOT_DESC, "")
        image.from_lab = booking.lab
        image.name = name
        image.description = description
        image.public = False
        image.lab_id = -1
        image.owner = owner
        image.host_type = host.profile
        image.save()
        try:
            current_image = host.config.image
            image.os = current_image.os
            image.save()
        except Exception:
            pass
        JobFactory.makeSnapshotTask(image, booking, host)

        self.el[self.RESULT] = image
        self.el[self.HAS_RESULT] = True

    def make_generic_resource_bundle(self):
        owner = self.el[self.SESSION_USER]
        if self.RESOURCE_TEMPLATE_MODELS in self.el:
            models = self.el[self.RESOURCE_TEMPLATE_MODELS]
            models['template'].owner = owner
            models['template'].temporary = False
            models['template'].save()
            self.el[self.RESULT] = models['template']
            self.el[self.HAS_RESULT] = True
            return False

        else:
            return "GRB no models given. CODE:0x0001"

    def make_software_config_bundle(self):
        models = self.el[self.CONFIG_MODELS]
        if 'bundle' in models:
            bundle = models['bundle']
            bundle.bundle = self.el[self.SELECTED_RESOURCE_TEMPLATE]
            try:
                bundle.save()
            except Exception as e:
                return "SWC, saving bundle generated exception: " + str(e) + "CODE:0x0007"

        else:
            return "SWC, no bundle in models. CODE:0x0006"
        if 'host_configs' in models:
            host_configs = models['host_configs']
            for host_config in host_configs:
                host_config.template = host_config.template
                host_config.profile = host_config.profile
                try:
                    host_config.save()
                except Exception as e:
                    return "SWC, saving host configs generated exception: " + str(e) + "CODE:0x0009"
        else:
            return "SWC, no host configs in models. CODE:0x0008"
        if 'opnfv' in models:
            opnfvconfig = models['opnfv']
            opnfvconfig.bundle = opnfvconfig.bundle
            if opnfvconfig.scenario not in opnfvconfig.installer.sup_scenarios.all():
                return "SWC, scenario not supported by installer. CODE:0x000d"
            try:
                opnfvconfig.save()
            except Exception as e:
                return "SWC, saving opnfv config generated exception: " + str(e) + "CODE:0x000b"
        else:
            pass

        self.el[self.RESULT] = bundle
        return False

    @transaction.atomic  # TODO: Rewrite transactions with savepoints at user level for all workflows
    def make_booking(self):
        models = self.el[self.BOOKING_MODELS]
        owner = self.el[self.SESSION_USER]

        if 'booking' in models:
            booking = models['booking']
        else:
            return "BOOK, no booking model exists. CODE:0x000f"

        selected_grb = None

        if self.SELECTED_RESOURCE_TEMPLATE in self.el:
            selected_grb = self.el[self.SELECTED_RESOURCE_TEMPLATE]
        else:
            return "BOOK, no selected resource. CODE:0x000e"

        if not booking.start:
            return "BOOK, booking has no start. CODE:0x0010"
        if not booking.end:
            return "BOOK, booking has no end. CODE:0x0011"
        if booking.end <= booking.start:
            return "BOOK, end before/same time as start. CODE:0x0012"

        if 'collaborators' in models:
            collaborators = models['collaborators']
        else:
            return "BOOK, collaborators not defined. CODE:0x0013"
        try:
            res_manager = ResourceManager.getInstance()
            resource_bundle = res_manager.instantiateTemplate(selected_grb)
        except ResourceAvailabilityException as e:
            return "BOOK, requested resources are not available. Exception: " + str(e) + " CODE:0x0014"
        except ModelValidationException as e:
            return "Error encountered when saving bundle. " + str(e) + " CODE: 0x001b"

        booking.resource = resource_bundle
        booking.owner = owner
        booking.lab = selected_grb.lab

        is_allowed = BookingAuthManager().booking_allowed(booking, self)
        if not is_allowed:
            return "BOOK, you are not allowed to book the requested resources"

        try:
            booking.save()
        except Exception as e:
            return "BOOK, saving booking generated exception: " + str(e) + " CODE:0x0015"

        for collaborator in collaborators:
            booking.collaborators.add(collaborator)

        try:
            booking.pdf = PDFTemplater.makePDF(booking)
            booking.save()
        except Exception as e:
            return "BOOK, failed to create Pod Desriptor File: " + str(e)

        try:
            JobFactory.makeCompleteJob(booking)
        except Exception as e:
            return "BOOK, serializing for api generated exception: " + str(e) + " CODE:0xFFFF"

        try:
            booking.save()
        except Exception as e:
            return "BOOK, saving booking generated exception: " + str(e) + " CODE:0x0016"

        self.el[self.RESULT] = booking
        self.el[self.HAS_RESULT] = True

    def make_opnfv_config(self):
        opnfv_models = self.el[self.OPNFV_MODELS]
        config_bundle = self.el[self.SELECTED_CONFIG_BUNDLE]
        if not config_bundle:
            return "No Configuration bundle selected"
        info = opnfv_models.get("meta", {})
        name = info.get("name", False)
        desc = info.get("description", False)
        if not (name and desc):
            return "No name or description given"
        installer = opnfv_models['installer_chosen']
        if not installer:
            return "No OPNFV Installer chosen"
        scenario = opnfv_models['scenario_chosen']
        if not scenario:
            return "No OPNFV Scenario chosen"

        opnfv_config = OPNFVConfig.objects.create(
            bundle=config_bundle,
            name=name,
            description=desc,
            installer=installer,
            scenario=scenario
        )

        network_roles = opnfv_models['network_roles']
        for net_role in network_roles:
            opnfv_config.networks.add(
                NetworkRole.objects.create(
                    name=net_role['role'],
                    network=net_role['network']
                )
            )

        host_roles = opnfv_models['host_roles']
        for host_role in host_roles:
            config = config_bundle.hostConfigurations.get(
                host__resource__name=host_role['host_name']
            )
            ResourceOPNFVConfig.objects.create(
                role=host_role['role'],
                host_config=config,
                opnfv_config=opnfv_config
            )

        self.el[self.RESULT] = opnfv_config
        self.el[self.HAS_RESULT] = True

    def __init__(self):
        self.el = {}
        self.el[self.CONFIRMATION] = {}
        self.el["active_step"] = 0
        self.el[self.HAS_RESULT] = False
        self.el[self.RESULT] = None
        self.get_history = {}
        self.put_history = {}
