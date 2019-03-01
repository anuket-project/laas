##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.shortcuts import render
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone

import yaml
import requests

from workflow.forms import ConfirmationForm
from api.models import JobFactory
from dashboard.exceptions import ResourceAvailabilityException, ModelValidationException
from resource_inventory.models import Image, GenericInterface
from resource_inventory.resource_manager import ResourceManager
from resource_inventory.pdf_templater import PDFTemplater
from notifier.manager import NotificationHandler
from booking.models import Booking


class BookingAuthManager():
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
        will return the PTL in the INFO file on success, or None
        """
        if "github" in info_url:
            return self.parse_github_url(info_url)

        if "gerrit.opnfv.org" in info_url:
            return self.parse_gerrit_url(info_url)

        if "git.opnfv.org" in info_url:
            return self.parse_opnfv_git_url(info_url)

    def booking_allowed(self, booking, repo):
        """
        This is the method that will have to change whenever the booking policy changes in the Infra
        group / LFN. This is a nice isolation of that administration crap
        currently checks if the booking uses multiple servers. if it does, then the owner must be a PTL,
        which is checked using the provided info file
        """
        if len(booking.resource.template.getHosts()) < 2:
            return True  # if they only have one server, we dont care
        if booking.owner.userprofile.booking_privledge:
            return True  # admin override for this user
        if repo.BOOKING_INFO_FILE not in repo.el:
            return False  # INFO file not provided
        ptl_info = self.parse_url(repo.el.get(repo.BOOKING_INFO_FILE))
        for ptl in ptl_info:
            if ptl['email'] == booking.owner.userprofile.email_addr:
                return True
        return False


class WorkflowStep(object):
    template = 'bad_request.html'
    title = "Generic Step"
    description = "You were led here by mistake"
    short_title = "error"
    metastep = None

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
        self.context = self.get_context()
        return render(request, self.template, self.context)

    def post_render(self, request):
        return self.render(request)

    def test_render(self, request):
        if request.method == "POST":
            return self.post_render(request)
        return self.render(request)

    def validate(self, request):
        pass

    def repo_get(self, key, default=None):
        return self.repo.get(key, default, self.id)

    def repo_put(self, key, value):
        return self.repo.put(key, value, self.id)


class Confirmation_Step(WorkflowStep):
    template = 'workflow/confirm.html'
    title = "Confirm Changes"
    description = "Does this all look right?"

    def get_vlan_warning(self):
        grb = self.repo_get(self.repo.SELECTED_GRESOURCE_BUNDLE, False)
        if not grb:
            return 0
        if self.repo.BOOKING_MODELS not in self.repo.el:
            return 0
        vlan_manager = grb.lab.vlan_manager
        if vlan_manager is None:
            return 0
        hosts = grb.getHosts()
        for host in hosts:
            for interface in host.generic_interfaces.all():
                for vlan in interface.vlans.all():
                    if vlan.public:
                        if not vlan_manager.public_vlan_is_available(vlan.vlan_id):
                            return 1
                    else:
                        if not vlan_manager.is_available(vlan.vlan_id):
                            return 1  # There is a problem with these vlans
        return 0

    def get_context(self):
        context = super(Confirmation_Step, self).get_context()
        context['form'] = ConfirmationForm()
        context['confirmation_info'] = yaml.dump(
            self.repo_get(self.repo.CONFIRMATION),
            default_flow_style=False
        ).strip()
        context['vlan_warning'] = self.get_vlan_warning()

        return context

    def flush_to_db(self):
        errors = self.repo.make_models()
        if errors:
            return errors

    def post_render(self, request):
        form = ConfirmationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data['confirm']
            context = self.get_context()
            if data == "True":
                context["bypassed"] = "true"
                errors = self.flush_to_db()
                if errors:
                    messages.add_message(request, messages.ERROR, "ERROR OCCURRED: " + errors)
                else:
                    messages.add_message(request, messages.SUCCESS, "Confirmed")

                return HttpResponse('')
            elif data == "False":
                context["bypassed"] = "true"
                messages.add_message(request, messages.SUCCESS, "Canceled")
                return render(request, self.template, context)
            else:
                pass

        else:
            if "vlan_input" in request.POST:
                if request.POST.get("vlan_input") == "True":
                    self.translate_vlans()
                    return self.render(request)
            pass

    def translate_vlans(self):
        grb = self.repo_get(self.repo.SELECTED_GRESOURCE_BUNDLE, False)
        if not grb:
            return 0
        vlan_manager = grb.lab.vlan_manager
        if vlan_manager is None:
            return 0
        hosts = grb.getHosts()
        for host in hosts:
            for interface in host.generic_interfaces.all():
                for vlan in interface.vlans.all():
                    if not vlan.public:
                        if not vlan_manager.is_available(vlan.vlan_id):
                            vlan.vlan_id = vlan_manager.get_vlan()
                            vlan.save()
                    else:
                        if not vlan_manager.public_vlan_is_available(vlan.vlan_id):
                            pub_vlan = vlan_manager.get_public_vlan()
                            vlan.vlan_id = pub_vlan.vlan
                            vlan.save()


class Workflow():

    steps = []
    active_index = 0


class Repository():

    EDIT = "editing"
    MODELS = "models"
    RESOURCE_SELECT = "resource_select"
    CONFIRMATION = "confirmation"
    SELECTED_GRESOURCE_BUNDLE = "selected generic bundle pk"
    SELECTED_CONFIG_BUNDLE = "selected config bundle pk"
    GRESOURCE_BUNDLE_MODELS = "generic_resource_bundle_models"
    GRESOURCE_BUNDLE_INFO = "generic_resource_bundle_info"
    BOOKING = "booking"
    LAB = "lab"
    GRB_LAST_HOSTLIST = "grb_network_previous_hostlist"
    BOOKING_FORMS = "booking_forms"
    SWCONF_HOSTS = "swconf_hosts"
    BOOKING_MODELS = "booking models"
    CONFIG_MODELS = "configuration bundle models"
    SESSION_USER = "session owner user account"
    VALIDATED_MODEL_GRB = "valid grb config model instance in db"
    VALIDATED_MODEL_CONFIG = "valid config model instance in db"
    VALIDATED_MODEL_BOOKING = "valid booking model instance in db"
    VLANS = "a list of vlans"
    SNAPSHOT_MODELS = "the models for snapshotting"
    SNAPSHOT_BOOKING_ID = "the booking id for snapshotting"
    SNAPSHOT_NAME = "the name of the snapshot"
    SNAPSHOT_DESC = "description of the snapshot"
    BOOKING_INFO_FILE = "the INFO.yaml file for this user's booking"

    # migratory elements of segmented workflow
    # each of these is the end result of a different workflow.
    HAS_RESULT = "whether or not workflow has a result"
    RESULT_KEY = "key for target index that result will be put into in parent"
    RESULT = "result object from workflow"

    def get_child_defaults(self):
        return_tuples = []
        for key in [self.SELECTED_GRESOURCE_BUNDLE, self.SESSION_USER]:
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

    def make_models(self):
        if self.SNAPSHOT_MODELS in self.el:
            errors = self.make_snapshot()
            if errors:
                return errors
        # if GRB WF, create it
        if self.GRESOURCE_BUNDLE_MODELS in self.el:
            errors = self.make_generic_resource_bundle()
            if errors:
                return errors
            else:
                self.el[self.HAS_RESULT] = True
                self.el[self.RESULT_KEY] = self.SELECTED_GRESOURCE_BUNDLE
                return

        if self.CONFIG_MODELS in self.el:
            errors = self.make_software_config_bundle()
            if errors:
                return errors
            else:
                self.el[self.HAS_RESULT] = True
                self.el[self.RESULT_KEY] = self.SELECTED_CONFIG_BUNDLE
                return

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

    def make_generic_resource_bundle(self):
        owner = self.el[self.SESSION_USER]
        if self.GRESOURCE_BUNDLE_MODELS in self.el:
            models = self.el[self.GRESOURCE_BUNDLE_MODELS]
            if 'hosts' in models:
                hosts = models['hosts']
            else:
                return "GRB has no hosts. CODE:0x0002"
            if 'bundle' in models:
                bundle = models['bundle']
            else:
                return "GRB, no bundle in models. CODE:0x0003"

            try:
                bundle.owner = owner
                bundle.save()
            except Exception as e:
                return "GRB, saving bundle generated exception: " + str(e) + " CODE:0x0004"
            try:
                for host in hosts:
                    genericresource = host.resource
                    genericresource.bundle = bundle
                    genericresource.save()
                    host.resource = genericresource
                    host.save()
            except Exception as e:
                return "GRB, saving hosts generated exception: " + str(e) + " CODE:0x0005"

            if 'interfaces' in models:
                for interface_set in models['interfaces'].values():
                    for interface in interface_set:
                        try:
                            interface.host = interface.host
                            interface.save()
                        except Exception:
                            return "GRB, saving interface " + str(interface) + " failed. CODE:0x0019"
            else:
                return "GRB, no interface set provided. CODE:0x001a"

            if 'vlans' in models:
                for resource_name, mapping in models['vlans'].items():
                    for profile_name, vlan_set in mapping.items():
                        interface = GenericInterface.objects.get(
                            profile__name=profile_name,
                            host__resource__name=resource_name,
                            host__resource__bundle=models['bundle']
                        )
                        for vlan in vlan_set:
                            try:
                                vlan.save()
                                interface.vlans.add(vlan)
                            except Exception as e:
                                return "GRB, saving vlan " + str(vlan) + " failed. Exception: " + str(e) + ". CODE:0x0017"
            else:
                return "GRB, no vlan set provided. CODE:0x0018"

        else:
            return "GRB no models given. CODE:0x0001"

        self.el[self.RESULT] = bundle
        return False

    def make_software_config_bundle(self):
        models = self.el[self.CONFIG_MODELS]
        if 'bundle' in models:
            bundle = models['bundle']
            bundle.bundle = bundle.bundle
            try:
                bundle.save()
            except Exception as e:
                return "SWC, saving bundle generated exception: " + str(e) + "CODE:0x0007"

        else:
            return "SWC, no bundle in models. CODE:0x0006"
        if 'host_configs' in models:
            host_configs = models['host_configs']
            for host_config in host_configs:
                host_config.bundle = host_config.bundle
                host_config.host = host_config.host
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

    def make_booking(self):
        models = self.el[self.BOOKING_MODELS]
        owner = self.el[self.SESSION_USER]

        if self.SELECTED_GRESOURCE_BUNDLE in self.el:
            selected_grb = self.el[self.SELECTED_GRESOURCE_BUNDLE]
        else:
            return "BOOK, no selected resource. CODE:0x000e"

        if not self.reserve_vlans(selected_grb):
            return "BOOK, vlans not available"

        if 'booking' in models:
            booking = models['booking']
        else:
            return "BOOK, no booking model exists. CODE:0x000f"

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
            resource_bundle = ResourceManager.getInstance().convertResourceBundle(selected_grb, config=booking.config_bundle)
        except ResourceAvailabilityException as e:
            return "BOOK, requested resources are not available. Exception: " + str(e) + " CODE:0x0014"
        except ModelValidationException as e:
            return "Error encountered when saving bundle. " + str(e) + " CODE: 0x001b"

        booking.resource = resource_bundle
        booking.owner = owner
        booking.config_bundle = booking.config_bundle
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
            booking.pdf = PDFTemplater.makePDF(booking.resource)
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

    def reserve_vlans(self, grb):
        """
        True is success
        """
        vlans = []
        public_vlan = None
        vlan_manager = grb.lab.vlan_manager
        if vlan_manager is None:
            return True
        for host in grb.getHosts():
            for interface in host.generic_interfaces.all():
                for vlan in interface.vlans.all():
                    if vlan.public:
                        public_vlan = vlan
                    else:
                        vlans.append(vlan.vlan_id)

        try:
            vlan_manager.reserve_vlans(vlans)
            vlan_manager.reserve_public_vlan(public_vlan.vlan_id)
            return True
        except Exception:
            return False

    def __init__(self):
        self.el = {}
        self.el[self.CONFIRMATION] = {}
        self.el["active_step"] = 0
        self.get_history = {}
        self.put_history = {}
