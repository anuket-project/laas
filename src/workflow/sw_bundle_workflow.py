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
from workflow.forms import BasicMetaForm, HostSoftwareDefinitionForm
from workflow.booking_workflow import Resource_Select
from resource_inventory.models import Image, GenericHost, ConfigBundle, HostConfiguration


# resource selection step is reused from Booking workflow
class SWConf_Resource_Select(Resource_Select):
    def __init__(self, *args, **kwargs):
        super(SWConf_Resource_Select, self).__init__(*args, **kwargs)
        self.repo_key = self.repo.SELECTED_GRESOURCE_BUNDLE
        self.confirm_key = "configuration"

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

    def build_filter_data(self, hosts_data):
        """
        returns a 2D array of images to exclude
        based on the ordering of the passed
        hosts_data
        """
        filter_data = []
        user = self.repo_get(self.repo.SESSION_USER)
        lab = self.repo_get(self.repo.SELECTED_GRESOURCE_BUNDLE).lab
        for i, host_data in enumerate(hosts_data):
            host = GenericHost.objects.get(pk=host_data['host_id'])
            wrong_owner = Image.objects.exclude(owner=user).exclude(public=True)
            wrong_host = Image.objects.exclude(host_type=host.profile)
            wrong_lab = Image.objects.exclude(from_lab=lab)
            excluded_images = wrong_owner | wrong_host | wrong_lab
            filter_data.append([])
            for image in excluded_images:
                filter_data[i].append(image.pk)
        return filter_data

    def create_hostformset(self, hostlist, data=None):
        hosts_initial = []
        host_configs = self.repo_get(self.repo.CONFIG_MODELS, {}).get("host_configs", False)
        if host_configs:
            for config in host_configs:
                hosts_initial.append({
                    'host_id': config.host.id,
                    'host_name': config.host.resource.name,
                    'headnode': config.is_head_node,
                    'image': config.image
                })
        else:
            for host in hostlist:
                hosts_initial.append({
                    'host_id': host.id,
                    'host_name': host.resource.name
                })

        HostFormset = formset_factory(HostSoftwareDefinitionForm, extra=0)
        filter_data = self.build_filter_data(hosts_initial)

        class SpecialHostFormset(HostFormset):
            def get_form_kwargs(self, index):
                kwargs = super(SpecialHostFormset, self).get_form_kwargs(index)
                if index is not None:
                    kwargs['imageQS'] = Image.objects.exclude(pk__in=filter_data[index])
                return kwargs

        if data:
            return SpecialHostFormset(data, initial=hosts_initial)
        return SpecialHostFormset(initial=hosts_initial)

    def get_host_list(self, grb=None):
        if grb is None:
            grb = self.repo_get(self.repo.SELECTED_GRESOURCE_BUNDLE, False)
            if not grb:
                return []
        if grb.id:
            return GenericHost.objects.filter(resource__bundle=grb)
        generic_hosts = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {}).get("hosts", [])
        return generic_hosts

    def get_context(self):
        context = super(Define_Software, self).get_context()

        grb = self.repo_get(self.repo.SELECTED_GRESOURCE_BUNDLE, False)

        if grb:
            context["grb"] = grb
            formset = self.create_hostformset(self.get_host_list(grb))
            context["formset"] = formset
            context['headnode'] = self.repo_get(self.repo.CONFIG_MODELS, {}).get("headnode_index", 1)
        else:
            context["error"] = "Please select a resource first"
            self.metastep.set_invalid("Step requires information that is not yet provided by previous step")

        return context

    def post_render(self, request):
        models = self.repo_get(self.repo.CONFIG_MODELS, {})
        if "bundle" not in models:
            models['bundle'] = ConfigBundle(owner=self.repo_get(self.repo.SESSION_USER))

        confirm = self.repo_get(self.repo.CONFIRMATION, {})

        hosts = self.get_host_list()
        models['headnode_index'] = request.POST.get("headnode", 1)
        formset = self.create_hostformset(hosts, data=request.POST)
        has_headnode = False
        if formset.is_valid():
            models['host_configs'] = []
            confirm_hosts = []
            for i, form in enumerate(formset):
                host = hosts[i]
                image = form.cleaned_data['image']
                headnode = form.cleaned_data['headnode']
                if headnode:
                    has_headnode = True
                bundle = models['bundle']
                hostConfig = HostConfiguration(
                    host=host,
                    image=image,
                    bundle=bundle,
                    is_head_node=headnode
                )
                models['host_configs'].append(hostConfig)
                confirm_hosts.append({
                    "name": host.resource.name,
                    "image": image.name,
                    "headnode": headnode
                })

            if not has_headnode:
                self.metastep.set_invalid('Must have one "Headnode" per POD')
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
        context["form"] = BasicMetaForm(initial=initial)
        return context

    def post_render(self, request):
        models = self.repo_get(self.repo.CONFIG_MODELS, {})
        if "bundle" not in models:
            models['bundle'] = ConfigBundle(owner=self.repo_get(self.repo.SESSION_USER))

        confirm = self.repo_get(self.repo.CONFIRMATION, {})
        if "configuration" not in confirm:
            confirm['configuration'] = {}

        form = BasicMetaForm(request.POST)
        if form.is_valid():
            models['bundle'].name = form.cleaned_data['name']
            models['bundle'].description = form.cleaned_data['description']

            confirm['configuration']['name'] = form.cleaned_data['name']
            confirm['configuration']['description'] = form.cleaned_data['description']
            self.metastep.set_valid("Complete")
        else:
            self.metastep.set_invalid("Please correct the errors shown below")

        self.repo_put(self.repo.CONFIG_MODELS, models)
        self.repo_put(self.repo.CONFIRMATION, confirm)

        return self.render(request)
