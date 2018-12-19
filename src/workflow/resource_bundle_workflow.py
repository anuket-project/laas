##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.shortcuts import render
from django.forms import formset_factory

import json
import re
from xml.dom import minidom

from workflow.models import WorkflowStep
from account.models import Lab
from workflow.forms import (
    HardwareDefinitionForm,
    NetworkDefinitionForm,
    ResourceMetaForm,
    GenericHostMetaForm
)
from resource_inventory.models import (
    GenericResourceBundle,
    Vlan,
    GenericInterface,
    GenericHost,
    GenericResource,
    HostProfile
)
from dashboard.exceptions import (
    InvalidVlanConfigurationException,
    NetworkExistsException,
    InvalidHostnameException,
    NonUniqueHostnameException,
    ResourceAvailabilityException
)

import logging
logger = logging.getLogger(__name__)


class Define_Hardware(WorkflowStep):

    template = 'resource/steps/define_hardware.html'
    title = "Define Hardware"
    description = "Choose the type and amount of machines you want"
    short_title = "hosts"

    def get_context(self):
        context = super(Define_Hardware, self).get_context()
        selection_data = {"hosts": {}, "labs": {}}
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
        hosts = models.get("hosts", [])
        for host in hosts:
            profile_id = "host_" + str(host.profile.id)
            if profile_id not in selection_data['hosts']:
                selection_data['hosts'][profile_id] = []
            selection_data['hosts'][profile_id].append({"host_name": host.resource.name, "class": profile_id})

        if models.get("bundle", GenericResourceBundle()).lab:
            selection_data['labs'] = {"lab_" + str(models.get("bundle").lab.lab_user.id): "true"}

        form = HardwareDefinitionForm(
            selection_data=selection_data
        )
        context['form'] = form
        return context

    def render(self, request):
        self.context = self.get_context()
        return render(request, self.template, self.context)

    def update_models(self, data):
        data = json.loads(data['filter_field'])
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
        models['hosts'] = []  # This will always clear existing data when this step changes
        models['interfaces'] = {}
        if "bundle" not in models:
            models['bundle'] = GenericResourceBundle(owner=self.repo_get(self.repo.SESSION_USER))
        host_data = data['hosts']
        names = {}
        for host_dict in host_data:
            id = host_dict['class']
            # bit of formatting
            id = int(id.split("_")[-1])
            profile = HostProfile.objects.get(id=id)
            # instantiate genericHost and store in repo
            name = host_dict['host_name']
            if not re.match(r"(?=^.{1,253}$)(^([A-Za-z0-9-_]{1,62}\.)*[A-Za-z0-9-_]{1,63})", name):
                raise InvalidHostnameException("Hostname must comply to RFC 952 and all extensions to it until this point")
            if name in names:
                raise NonUniqueHostnameException("All hosts must have unique names")
            names[name] = True
            genericResource = GenericResource(bundle=models['bundle'], name=name)
            genericHost = GenericHost(profile=profile, resource=genericResource)
            models['hosts'].append(genericHost)
            for interface_profile in profile.interfaceprofile.all():
                genericInterface = GenericInterface(profile=interface_profile, host=genericHost)
                if genericHost.resource.name not in models['interfaces']:
                    models['interfaces'][genericHost.resource.name] = []
                models['interfaces'][genericHost.resource.name].append(genericInterface)

        # add selected lab to models
        for lab_dict in data['labs']:
            if list(lab_dict.values())[0]:  # True for lab the user selected
                lab_user_id = int(list(lab_dict.keys())[0].split("_")[-1])
                models['bundle'].lab = Lab.objects.get(lab_user__id=lab_user_id)
                break  # if somehow we get two 'true' labs, we only use one

        # return to repo
        self.repo_put(self.repo.GRESOURCE_BUNDLE_MODELS, models)

    def update_confirmation(self):
        confirm = self.repo_get(self.repo.CONFIRMATION, {})
        if "resource" not in confirm:
            confirm['resource'] = {}
        confirm['resource']['hosts'] = []
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {"hosts": []})
        for host in models['hosts']:
            host_dict = {"name": host.resource.name, "profile": host.profile.name}
            confirm['resource']['hosts'].append(host_dict)
        if "lab" in models:
            confirm['resource']['lab'] = models['lab'].lab_user.username
        self.repo_put(self.repo.CONFIRMATION, confirm)

    def post_render(self, request):
        try:
            self.form = HardwareDefinitionForm(request.POST)
            if self.form.is_valid():
                if len(json.loads(self.form.cleaned_data['filter_field']).labs) != 1:
                    self.metastep.set_invalid("Please select one lab")
                else:
                    self.update_models(self.form.cleaned_data)
                    self.update_confirmation()
                    self.metastep.set_valid("Step Completed")
            else:
                self.metastep.set_invalid("Please complete the fields highlighted in red to continue")
                pass
        except Exception as e:
            self.metastep.set_invalid(str(e))
        self.context = self.get_context()
        return render(request, self.template, self.context)


class Define_Nets(WorkflowStep):
    template = 'resource/steps/pod_definition.html'
    title = "Define Networks"
    description = "Use the tool below to draw the network topology of your POD"
    short_title = "networking"
    form = NetworkDefinitionForm

    def get_vlans(self):
        vlans = self.repo_get(self.repo.VLANS)
        if vlans:
            return vlans
        # try to grab some vlans from lab
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
        if "bundle" not in models:
            return None
        lab = models['bundle'].lab
        if lab is None or lab.vlan_manager is None:
            return None
        try:
            vlans = lab.vlan_manager.get_vlan(count=lab.vlan_manager.block_size)
            self.repo_put(self.repo.VLANS, vlans)
            return vlans
        except Exception:
            return None

    def get_context(self):
        # TODO: render *primarily* on hosts in repo models
        context = super(Define_Nets, self).get_context()
        context['form'] = NetworkDefinitionForm()
        try:
            context['hosts'] = []
            models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
            vlans = self.get_vlans()
            if vlans:
                context['vlans'] = vlans
            hosts = models.get("hosts", [])
            hostlist = self.repo_get(self.repo.GRB_LAST_HOSTLIST, None)
            added_list = []
            added_dict = {}
            context['added_hosts'] = []
            if hostlist is not None:
                new_hostlist = []
                for host in models['hosts']:
                    intcount = host.profile.interfaceprofile.count()
                    new_hostlist.append(str(host.resource.name) + "*" + str(host.profile) + "&" + str(intcount))
                context['removed_hosts'] = list(set(hostlist) - set(new_hostlist))
                added_list = list(set(new_hostlist) - set(hostlist))
                for hoststr in added_list:
                    key = hoststr.split("*")[0]
                    added_dict[key] = hoststr
            for generic_host in hosts:
                host_profile = generic_host.profile
                host = {}
                host['id'] = generic_host.resource.name
                host['interfaces'] = []
                for iface in host_profile.interfaceprofile.all():
                    host['interfaces'].append(
                        {
                            "name": iface.name,
                            "description": "speed: " + str(iface.speed) + "M\ntype: " + iface.nic_type
                        }
                    )
                host['value'] = {"name": generic_host.resource.name}
                host['value']['description'] = generic_host.profile.description
                context['hosts'].append(json.dumps(host))
                if host['id'] in added_dict:
                    context['added_hosts'].append(json.dumps(host))
            bundle = models.get("bundle", False)
            if bundle and bundle.xml:
                context['xml'] = bundle.xml
            else:
                context['xml'] = False

        except Exception:
            pass

        return context

    def post_render(self, request):
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
        if 'hosts' in models:
            hostlist = []
            for host in models['hosts']:
                intcount = host.profile.interfaceprofile.count()
                hostlist.append(str(host.resource.name) + "*" + str(host.profile) + "&" + str(intcount))
            self.repo_put(self.repo.GRB_LAST_HOSTLIST, hostlist)
        try:
            xmlData = request.POST.get("xml")
            self.updateModels(xmlData)
            # update model with xml
            self.metastep.set_valid("Networks applied successfully")
        except ResourceAvailabilityException:
            self.metastep.set_invalid("Public network not availble")
        except Exception:
            self.metastep.set_invalid("An error occurred when applying networks")
        return self.render(request)

    def updateModels(self, xmlData):
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
        models["vlans"] = {}
        given_hosts, interfaces = self.parseXml(xmlData)
        vlan_manager = models['bundle'].lab.vlan_manager
        existing_host_list = models.get("hosts", [])
        existing_hosts = {}  # maps id to host
        for host in existing_host_list:
            existing_hosts[host.resource.name] = host

        bundle = models.get("bundle", GenericResourceBundle(owner=self.repo_get(self.repo.SESSION_USER)))

        for hostid, given_host in given_hosts.items():
            existing_host = existing_hosts[hostid[5:]]

            for ifaceId in given_host['interfaces']:
                iface = interfaces[ifaceId]
                if existing_host.resource.name not in models['vlans']:
                    models['vlans'][existing_host.resource.name] = {}
                models['vlans'][existing_host.resource.name][iface['profile_name']] = []
                for network in iface['networks']:
                    vlan_id = network['network']['vlan']
                    is_public = network['network']['public']
                    if is_public:
                        public_net = vlan_manager.get_public_vlan()
                        if public_net is None:
                            raise ResourceAvailabilityException("No public networks available")
                        vlan_id = vlan_manager.get_public_vlan().vlan
                    vlan = Vlan(vlan_id=vlan_id, tagged=network['tagged'], public=is_public)
                    models['vlans'][existing_host.resource.name][iface['profile_name']].append(vlan)
        bundle.xml = xmlData
        self.repo_put(self.repo.GRESOURCE_BUNDLE_MODELS, models)

    # serialize and deserialize xml from mxGraph
    def parseXml(self, xmlString):
        parent_nets = {}  # map network ports to networks
        networks = {}  # maps net id to network object
        hosts = {}  # cotains id -> hosts, each containing interfaces, referencing networks
        interfaces = {}  # maps id -> interface
        xmlDom = minidom.parseString(xmlString)
        root = xmlDom.documentElement.firstChild
        netids = {}
        untagged_ints = {}
        for cell in root.childNodes:
            cellId = cell.getAttribute('id')

            if cell.getAttribute("edge"):
                # cell is a network connection
                escaped_json_str = cell.getAttribute("value")
                json_str = escaped_json_str.replace('&quot;', '"')
                attributes = json.loads(json_str)
                tagged = attributes['tagged']
                interface = None
                network = None
                src = cell.getAttribute("source")
                tgt = cell.getAttribute("target")
                if src in parent_nets:
                    # src is a network port
                    network = networks[parent_nets[src]]
                    if tgt in untagged_ints and not tagged:
                        raise InvalidVlanConfigurationException("More than one untagged vlan on an interface")
                    interface = interfaces[tgt]
                    untagged_ints[tgt] = True
                else:
                    network = networks[parent_nets[tgt]]
                    if src in untagged_ints and not tagged:
                        raise InvalidVlanConfigurationException("More than one untagged vlan on an interface")
                    interface = interfaces[src]
                    untagged_ints[src] = True
                interface['networks'].append({"network": network, "tagged": tagged})

            elif "network" in cellId:  # cell is a network
                escaped_json_str = cell.getAttribute("value")
                json_str = escaped_json_str.replace('&quot;', '"')
                net_info = json.loads(json_str)
                nid = net_info['vlan_id']
                public = net_info['public']
                try:
                    int_netid = int(nid)
                    assert public or int_netid > 1, "Net id is 1 or lower"
                    assert int_netid < 4095, "Net id is 4095 or greater"
                except Exception:
                    raise InvalidVlanConfigurationException("VLAN ID is not an integer more than 1 and less than 4095")
                if nid in netids:
                    raise NetworkExistsException("Non unique network id found")
                else:
                    pass
                network = {"name": net_info['name'], "vlan": net_info['vlan_id'], "public": public}
                netids[net_info['vlan_id']] = True
                networks[cellId] = network

            elif "host" in cellId:  # cell is a host/machine
                # TODO gather host info
                cell_json_str = cell.getAttribute("value")
                cell_json = json.loads(cell_json_str)
                host = {"interfaces": [], "name": cellId, "profile_name": cell_json['name']}
                hosts[cellId] = host

            elif cell.hasAttribute("parent"):
                parentId = cell.getAttribute('parent')
                if "network" in parentId:
                    parent_nets[cellId] = parentId
                elif "host" in parentId:
                    # TODO gather iface info
                    cell_json_str = cell.getAttribute("value")
                    cell_json = json.loads(cell_json_str)
                    iface = {"name": cellId, "networks": [], "profile_name": cell_json['name']}
                    hosts[parentId]['interfaces'].append(cellId)
                    interfaces[cellId] = iface
        return hosts, interfaces


class Resource_Meta_Info(WorkflowStep):
    template = 'resource/steps/meta_info.html'
    title = "Extra Info"
    description = "Please fill out the rest of the information about your resource"
    short_title = "pod info"

    def get_context(self):
        context = super(Resource_Meta_Info, self).get_context()
        name = ""
        desc = ""
        bundle = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {}).get("bundle", False)
        if bundle and bundle.name:
            name = bundle.name
            desc = bundle.description
        context['form'] = ResourceMetaForm(initial={"bundle_name": name, "bundle_description": desc})
        return context

    def post_render(self, request):
        form = ResourceMetaForm(request.POST)
        if form.is_valid():
            models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
            name = form.cleaned_data['bundle_name']
            desc = form.cleaned_data['bundle_description']
            bundle = models.get("bundle", GenericResourceBundle(owner=self.repo_get(self.repo.SESSION_USER)))
            bundle.name = name
            bundle.description = desc
            models['bundle'] = bundle
            self.repo_put(self.repo.GRESOURCE_BUNDLE_MODELS, models)
            confirm = self.repo_get(self.repo.CONFIRMATION)
            if "resource" not in confirm:
                confirm['resource'] = {}
            confirm_info = confirm['resource']
            confirm_info["name"] = name
            tmp = desc
            if len(tmp) > 60:
                tmp = tmp[:60] + "..."
            confirm_info["description"] = tmp
            self.repo_put(self.repo.CONFIRMATION, confirm)
            self.metastep.set_valid("Step Completed")

        else:
            self.metastep.set_invalid("Please correct the fields highlighted in red to continue")
            pass
        return self.render(request)


class Host_Meta_Info(WorkflowStep):
    template = "resource/steps/host_info.html"
    title = "Host Info"
    description = "We need a little bit of information about your chosen machines"
    short_title = "host info"

    def __init__(self, *args, **kwargs):
        super(Host_Meta_Info, self).__init__(*args, **kwargs)
        self.formset = formset_factory(GenericHostMetaForm, extra=0)

    def get_context(self):
        context = super(Host_Meta_Info, self).get_context()
        GenericHostFormset = self.formset
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
        initial_data = []
        if "hosts" not in models:
            context['error'] = "Please go back and select your hosts"
        else:
            for host in models['hosts']:
                profile = host.profile.name
                name = host.resource.name
                if not name:
                    name = ""
                initial_data.append({"host_profile": profile, "host_name": name})
        context['formset'] = GenericHostFormset(initial=initial_data)
        return context

    def post_render(self, request):
        models = self.repo_get(self.repo.GRESOURCE_BUNDLE_MODELS, {})
        if 'hosts' not in models:
            models['hosts'] = []
        hosts = models['hosts']
        i = 0
        confirm_hosts = []
        GenericHostFormset = self.formset
        formset = GenericHostFormset(request.POST)
        if formset.is_valid():
            for form in formset:
                host = hosts[i]
                host.resource.name = form.cleaned_data['host_name']
                i += 1
                confirm_hosts.append({"name": host.resource.name, "profile": host.profile.name})
            models['hosts'] = hosts
            self.repo_put(self.repo.GRESOURCE_BUNDLE_MODELS, models)
            confirm = self.repo_get(self.repo.CONFIRMATION, {})
            if "resource" not in confirm:
                confirm['resource'] = {}
            confirm['resource']['hosts'] = confirm_hosts
            self.repo_put(self.repo.CONFIRMATION, confirm)
        else:
            pass
        return self.render(request)
