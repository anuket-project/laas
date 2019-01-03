##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.forms import formset_factory

from workflow.models import WorkflowStep
from workflow.forms import SoftwareConfigurationForm, HostSoftwareDefinitionForm
from workflow.booking_workflow import Resource_Select
from resource_inventory.models import Image, GenericHost, ConfigBundle, HostConfiguration, Installer, OPNFVConfig


# resource selection step is reused from Booking workflow
class SWConf_Resource_Select(Resource_Select):
    def __init__(self, *args, **kwargs):
        super(SWConf_Resource_Select, self).__init__(*args, **kwargs)
        self.repo_key = self.repo.SWCONF_SELECTED_GRB
        self.confirm_key = "configuration"

    def get_default_entry(self):
        booking_grb = self.repo_get(self.repo.BOOKING_SELECTED_GRB)
        if booking_grb:
            return booking_grb
        created_grb = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {}).get("bundle", None)
        return created_grb

    def post_render(self, request):
        response = super(SWConf_Resource_Select, self).post_render(request)
        models = self.repo_get(self.repo.CONFIG_MODELS, {})
        bundle = models.get("bundle", ConfigBundle(owner=self.repo_get(self.repo.SESSION_USER)))
        bundle.bundle = self.repo_get(self.repo_key)  # super put grb here
        models['bundle'] = bundle
        self.repo_put(self.repo.CONFIG_MODELS, models)
        return response


class Define_Software(WorkflowStep):
    template = 'config_bundle/steps/define_software.html'
    title = "Pick Software"
    description = "Choose the opnfv and image of your machines"
    short_title = "host config"

    def create_hostformset(self, hostlist):
        hosts_initial = []
        host_configs = self.repo_get(self.repo.CONFIG_MODELS, {}).get("host_configs", False)
        if host_configs:
            for config in host_configs:
                host_initial = {'host_id': config.host.id, 'host_name': config.host.resource.name}
                host_initial['role'] = config.opnfvRole
                host_initial['image'] = config.image
                hosts_initial.append(host_initial)

        else:
            for host in hostlist:
                host_initial = {'host_id': host.id, 'host_name': host.resource.name}

                hosts_initial.append(host_initial)

        HostFormset = formset_factory(HostSoftwareDefinitionForm, extra=0)
        host_formset = HostFormset(initial=hosts_initial)

        filter_data = {}
        user = self.repo_get(self.repo.SESSION_USER)
        i = 0
        for host_data in hosts_initial:
            host_profile = None
            try:
                host = GenericHost.objects.get(pk=host_data['host_id'])
                host_profile = host.profile
            except Exception:
                for host in hostlist:
                    if host.resource.name == host_data['host_name']:
                        host_profile = host.profile
                        break
            excluded_images = Image.objects.exclude(owner=user).exclude(public=True)
            excluded_images = excluded_images | Image.objects.exclude(host_type=host.profile)
            lab = self.repo_get(self.repo.SWCONF_SELECTED_GRB).lab
            excluded_images = excluded_images | Image.objects.exclude(from_lab=lab)
            filter_data["id_form-" + str(i) + "-image"] = []
            for image in excluded_images:
                filter_data["id_form-" + str(i) + "-image"].append(image.name)
            i += 1

        return host_formset, filter_data

    def get_host_list(self, grb=None):
        if grb is None:
            grb = self.repo_get(self.repo.SWCONF_SELECTED_GRB, False)
            if not grb:
                return []
        if grb.id:
            return GenericHost.objects.filter(resource__bundle=grb)
        generic_hosts = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {}).get("hosts", [])
        return generic_hosts

    def get_context(self):
        context = super(Define_Software, self).get_context()

        grb = self.repo_get(self.repo.SWCONF_SELECTED_GRB, False)

        if grb:
            context["grb"] = grb
            formset, filter_data = self.create_hostformset(self.get_host_list(grb))
            context["formset"] = formset
            context["filter_data"] = filter_data
        else:
            context["error"] = "Please select a resource first"
            self.metastep.set_invalid("Step requires information that is not yet provided by previous step")

        return context

    def post_render(self, request):
        models = self.repo_get(self.repo.CONFIG_MODELS, {})
        if "bundle" not in models:
            models['bundle'] = ConfigBundle(owner=self.repo_get(self.repo.SESSION_USER))

        confirm = self.repo_get(self.repo.CONFIRMATION, {})

        HostFormset = formset_factory(HostSoftwareDefinitionForm, extra=0)
        formset = HostFormset(request.POST)
        hosts = self.get_host_list()
        has_jumphost = False
        if formset.is_valid():
            models['host_configs'] = []
            i = 0
            confirm_hosts = []
            for form in formset:
                host = hosts[i]
                i += 1
                image = form.cleaned_data['image']
                # checks image compatability
                grb = self.repo_get(self.repo.SWCONF_SELECTED_GRB)
                lab = None
                if grb:
                    lab = grb.lab
                try:
                    owner = self.repo_get(self.repo.SESSION_USER)
                    q = Image.objects.filter(owner=owner) | Image.objects.filter(public=True)
                    q.filter(host_type=host.profile)
                    q.filter(from_lab=lab)
                    q.get(id=image.id)  # will throw exception if image is not in q
                except:
                    self.metastep.set_invalid("Image " + image.name + " is not compatible with host " + host.resource.name)
                role = form.cleaned_data['role']
                if "jumphost" in role.name.lower():
                    has_jumphost = True
                bundle = models['bundle']
                hostConfig = HostConfiguration(
                    host=host,
                    image=image,
                    bundle=bundle,
                    opnfvRole=role
                )
                models['host_configs'].append(hostConfig)
                confirm_host = {"name": host.resource.name, "image": image.name, "role": role.name}
                confirm_hosts.append(confirm_host)

            if not has_jumphost:
                self.metastep.set_invalid('Must have at least one "Jumphost" per POD')
                return self.render(request)

            self.repo_put(self.repo.CONFIG_MODELS, models)
            if "configuration" not in confirm:
                confirm['configuration'] = {}
            confirm['configuration']['hosts'] = confirm_hosts
            self.repo_put(self.repo.CONFIRMATION, confirm)
            self.metastep.set_valid("Completed")
        else:
            self.metastep.set_invalid("Please complete all fields")

        return self.render(request)


class Config_Software(WorkflowStep):
    template = 'config_bundle/steps/config_software.html'
    form = SoftwareConfigurationForm
    context = {'workspace_form': form}
    title = "Other Info"
    description = "Give your software config a name, description, and other stuff"
    short_title = "config info"

    def get_context(self):
        context = super(Config_Software, self).get_context()

        initial = {}
        models = self.repo_get(self.repo.CONFIG_MODELS, {})
        bundle = models.get("bundle", False)
        if bundle:
            initial['name'] = bundle.name
            initial['description'] = bundle.description
        opnfv = models.get("opnfv", False)
        if opnfv:
            initial['installer'] = opnfv.installer
            initial['scenario'] = opnfv.scenario
        else:
            initial['opnfv'] = False
        supported = {}
        for installer in Installer.objects.all():
            supported[str(installer)] = []
            for scenario in installer.sup_scenarios.all():
                supported[str(installer)].append(str(scenario))

        context["form"] = SoftwareConfigurationForm(initial=initial)
        context['supported'] = supported

        return context

    def post_render(self, request):
        try:
            models = self.repo_get(self.repo.CONFIG_MODELS, {})
            if "bundle" not in models:
                models['bundle'] = ConfigBundle(owner=self.repo_get(self.repo.SESSION_USER))

            confirm = self.repo_get(self.repo.CONFIRMATION, {})
            if "configuration" not in confirm:
                confirm['configuration'] = {}

            form = self.form(request.POST)
            if form.is_valid():
                models['bundle'].name = form.cleaned_data['name']
                models['bundle'].description = form.cleaned_data['description']
                if form.cleaned_data['opnfv']:
                    installer = form.cleaned_data['installer']
                    scenario = form.cleaned_data['scenario']
                    opnfv = OPNFVConfig(
                        bundle=models['bundle'],
                        installer=installer,
                        scenario=scenario
                    )
                    models['opnfv'] = opnfv
                    confirm['configuration']['installer'] = form.cleaned_data['installer'].name
                    confirm['configuration']['scenario'] = form.cleaned_data['scenario'].name

                confirm['configuration']['name'] = form.cleaned_data['name']
                confirm['configuration']['description'] = form.cleaned_data['description']
                self.metastep.set_valid("Complete")
            else:
                self.metastep.set_invalid("Please correct the errors shown below")

            self.repo_put(self.repo.CONFIG_MODELS, models)
            self.repo_put(self.repo.CONFIRMATION, confirm)

        except Exception:
            pass
        return self.render(request)
