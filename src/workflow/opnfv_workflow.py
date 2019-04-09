##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.forms import formset_factory
from django.contrib import messages

import json

from workflow.models import WorkflowStep
from resource_inventory.models import ConfigBundle, OPNFV_SETTINGS
from workflow.forms import OPNFVSelectionForm, OPNFVNetworkRoleForm, OPNFVHostRoleForm, SWConfigSelectorForm, BasicMetaForm


class OPNFV_Resource_Select(WorkflowStep):
    template = 'booking/steps/swconfig_select.html'
    title = "Select Software Configuration"
    description = "Choose the software and related configurations you want to use to configure OPNFV"
    short_title = "software configuration"
    modified_key = "configbundle_step"

    def update_confirmation(self):
        confirm = self.repo_get(self.repo.CONFIRMATION, {})
        config_bundle = self.repo_get(self.repo.OPNFV_MODELS, {}).get("configbundle")
        if not config_bundle:
            return
        confirm['software bundle'] = config_bundle.name
        confirm['hardware POD'] = config_bundle.bundle.name
        self.repo_put(self.repo.CONFIRMATION, confirm)

    def post_render(self, request):
        models = self.repo_get(self.repo.OPNFV_MODELS, {})
        form = SWConfigSelectorForm(request.POST)
        if form.is_valid():
            bundle_json = form.cleaned_data['software_bundle']
            bundle_json = bundle_json[2:-2]  # Stupid django string bug
            if not bundle_json:
                self.metastep.set_invalid("Please select a valid config")
                return self.render(request)
            bundle_json = json.loads(bundle_json)
            if len(bundle_json) < 1:
                self.metastep.set_invalid("Please select a valid config")
                return self.render(request)
            bundle = None
            id = int(bundle_json[0]['id'])
            bundle = ConfigBundle.objects.get(id=id)

            models['configbundle'] = bundle
            self.repo_put(self.repo.OPNFV_MODELS, models)
            self.metastep.set_valid("Step Completed")
            messages.add_message(request, messages.SUCCESS, 'Form Validated Successfully', fail_silently=True)
            self.update_confirmation()
        else:
            self.metastep.set_invalid("Please select or create a valid config")
            messages.add_message(request, messages.ERROR, "Form Didn't Validate", fail_silently=True)

        return self.render(request)

    def get_context(self):
        context = super(OPNFV_Resource_Select, self).get_context()
        default = []
        user = self.repo_get(self.repo.SESSION_USER)

        context['form'] = SWConfigSelectorForm(chosen_software=default, bundle=None, edit=True, resource=None, user=user)
        return context


class Pick_Installer(WorkflowStep):
    template = 'config_bundle/steps/pick_installer.html'
    title = 'Pick OPNFV Installer'
    description = 'Choose which OPNFV installer to use'
    short_title = "opnfv installer"
    modified_key = "installer_step"

    def update_confirmation(self):
        confirm = self.repo_get(self.repo.CONFIRMATION, {})
        models = self.repo_get(self.repo.OPNFV_MODELS, {})
        installer = models.get("installer_chosen")
        scenario = models.get("scenario_chosen")
        if not (installer and scenario):
            return
        confirm['installer'] = installer.name
        confirm['scenario'] = scenario.name
        self.repo_put(self.repo.CONFIRMATION, confirm)

    def get_context(self):
        context = super(Pick_Installer, self).get_context()

        models = self.repo_get(self.repo.OPNFV_MODELS, None)
        initial = {
            "installer": models.get("installer_chosen"),
            "scenario": models.get("scenario_chosen")
        }

        context["form"] = OPNFVSelectionForm(initial=initial)
        return context

    def post_render(self, request):
        form = OPNFVSelectionForm(request.POST)
        if form.is_valid():
            installer = form.cleaned_data['installer']
            scenario = form.cleaned_data['scenario']
            models = self.repo_get(self.repo.OPNFV_MODELS, {})
            models['installer_chosen'] = installer
            models['scenario_chosen'] = scenario
            self.repo_put(self.repo.OPNFV_MODELS, models)
            self.update_confirmation()
            self.metastep.set_valid("Step Completed")
        else:
            self.metastep.set_invalid("Please select an Installer and Scenario")

        return self.render(request)


class Assign_Network_Roles(WorkflowStep):
    template = 'config_bundle/steps/assign_network_roles.html'
    title = 'Pick Network Roles'
    description = 'Choose what role each network should get'
    short_title = "network roles"
    modified_key = "net_roles_step"

    """
    to do initial filling, repo should have a "network_roles" array with the following structure for each element:
    {
        "role": <NetworkRole object ref>,
        "network": <Network object ref>
    }
    """
    def create_netformset(self, roles, config_bundle, data=None):
        roles_initial = []
        set_roles = self.repo_get(self.repo.OPNFV_MODELS, {}).get("network_roles")
        if set_roles:
            roles_initial = set_roles
        else:
            for role in OPNFV_SETTINGS.NETWORK_ROLES:
                roles_initial.append({"role": role})

        Formset = formset_factory(OPNFVNetworkRoleForm, extra=0)
        kwargs = {
            "initial": roles_initial,
            "form_kwargs": {"config_bundle": config_bundle}
        }
        formset = None
        if data:
            formset = Formset(data, **kwargs)
        else:
            formset = Formset(**kwargs)
        return formset

    def get_context(self):
        context = super(Assign_Network_Roles, self).get_context()
        config_bundle = self.repo_get(self.repo.OPNFV_MODELS, {}).get("configbundle")
        if config_bundle is None:
            context["unavailable"] = True
            return context

        roles = OPNFV_SETTINGS.NETWORK_ROLES
        formset = self.create_netformset(roles, config_bundle)
        context['formset'] = formset

        return context

    def update_confirmation(self):
        confirm = self.repo_get(self.repo.CONFIRMATION, {})
        models = self.repo_get(self.repo.OPNFV_MODELS, {})
        roles = models.get("network_roles")
        if not roles:
            return
        confirm['network roles'] = {}
        for role in roles:
            confirm['network roles'][role['role']] = role['network'].name
        self.repo_put(self.repo.CONFIRMATION, confirm)

    def post_render(self, request):
        models = self.repo_get(self.repo.OPNFV_MODELS, {})
        config_bundle = models.get("configbundle")
        roles = OPNFV_SETTINGS.NETWORK_ROLES
        net_role_formset = self.create_netformset(roles, config_bundle, data=request.POST)
        if net_role_formset.is_valid():
            results = []
            for form in net_role_formset:
                results.append({
                    "role": form.cleaned_data['role'],
                    "network": form.cleaned_data['network']
                })
            models['network_roles'] = results
            self.metastep.set_valid("Completed")
            self.repo_put(self.repo.OPNFV_MODELS, models)
            self.update_confirmation()
        else:
            self.metastep.set_invalid("Please complete all fields")
        return self.render(request)


class Assign_Host_Roles(WorkflowStep):  # taken verbatim from Define_Software in sw workflow, merge the two?
    template = 'config_bundle/steps/assign_host_roles.html'
    title = 'Pick Host Roles'
    description = "Choose the role each machine will have in your OPNFV pod"
    short_title = "host roles"
    modified_key = "host_roles_step"

    def create_host_role_formset(self, hostlist=[], data=None):
        models = self.repo_get(self.repo.OPNFV_MODELS, {})
        host_roles = models.get("host_roles", [])
        if not host_roles:
            for host in hostlist:
                initial = {"host_name": host.resource.name}
                host_roles.append(initial)
        models['host_roles'] = host_roles
        self.repo_put(self.repo.OPNFV_MODELS, models)

        HostFormset = formset_factory(OPNFVHostRoleForm, extra=0)

        kwargs = {"initial": host_roles}
        formset = None
        if data:
            formset = HostFormset(data, **kwargs)
        else:
            formset = HostFormset(**kwargs)

        return formset

    def get_context(self):
        context = super(Assign_Host_Roles, self).get_context()
        models = self.repo_get(self.repo.OPNFV_MODELS, {})
        config = models.get("configbundle")
        if config is None:
            context['error'] = "Please select a Configuration on the first step"

        formset = self.create_host_role_formset(hostlist=config.bundle.getHosts())
        context['formset'] = formset

        return context

    def get_host_role_mapping(self, host_roles, hostname):
        for obj in host_roles:
            if hostname == obj['host_name']:
                return obj
        return None

    def update_confirmation(self):
        confirm = self.repo_get(self.repo.CONFIRMATION, {})
        models = self.repo_get(self.repo.OPNFV_MODELS, {})
        roles = models.get("host_roles")
        if not roles:
            return
        confirm['host roles'] = {}
        for role in roles:
            confirm['host roles'][role['host_name']] = role['role'].name
        self.repo_put(self.repo.CONFIRMATION, confirm)

    def post_render(self, request):
        formset = self.create_host_role_formset(data=request.POST)

        models = self.repo_get(self.repo.OPNFV_MODELS, {})
        host_roles = models.get("host_roles", [])

        has_jumphost = False
        if formset.is_valid():
            for form in formset:
                hostname = form.cleaned_data['host_name']
                role = form.cleaned_data['role']
                mapping = self.get_host_role_mapping(host_roles, hostname)
                mapping['role'] = role
                if "jumphost" in role.name.lower():
                    has_jumphost = True

            models['host_roles'] = host_roles
            self.repo_put(self.repo.OPNFV_MODELS, models)
            self.update_confirmation()

            if not has_jumphost:
                self.metastep.set_invalid('Must have at least one "Jumphost" per POD')
            else:
                self.metastep.set_valid("Completed")
        else:
            self.metastep.set_invalid("Please complete all fields")

        return self.render(request)


class MetaInfo(WorkflowStep):
    template = 'config_bundle/steps/config_software.html'
    title = "Other Info"
    description = "Give your software config a name, description, and other stuff"
    short_title = "config info"

    def get_context(self):
        context = super(MetaInfo, self).get_context()

        initial = self.repo_get(self.repo.OPNFV_MODELS, {}).get("meta", {})
        context["form"] = BasicMetaForm(initial=initial)
        return context

    def update_confirmation(self):
        confirm = self.repo_get(self.repo.CONFIRMATION, {})
        models = self.repo_get(self.repo.OPNFV_MODELS, {})
        meta = models.get("meta")
        if not meta:
            return
        confirm['name'] = meta['name']
        confirm['description'] = meta['description']
        self.repo_put(self.repo.CONFIRMATION, confirm)

    def post_render(self, request):
        models = self.repo_get(self.repo.OPNFV_MODELS, {})
        info = models.get("meta", {})

        form = BasicMetaForm(request.POST)
        if form.is_valid():
            info['name'] = form.cleaned_data['name']
            info['description'] = form.cleaned_data['description']
            models['meta'] = info
            self.repo_put(self.repo.OPNFV_MODELS, models)
            self.update_confirmation()
            self.metastep.set_valid("Complete")
        else:
            self.metastep.set_invalid("Please correct the errors shown below")

        self.repo_put(self.repo.OPNFV_MODELS, models)
        return self.render(request)
