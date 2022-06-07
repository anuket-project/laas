##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.conf import settings
from django.forms import formset_factory
from django.core.exceptions import ValidationError

from typing import List

import re
import json
from xml.dom import minidom
import traceback

from workflow.models import WorkflowStep
from account.models import Lab
from workflow.forms import (
    HardwareDefinitionForm,
    NetworkDefinitionForm,
    ResourceMetaForm,
    HostSoftwareDefinitionForm,
)
from resource_inventory.models import (
    ResourceTemplate,
    ResourceConfiguration,
    InterfaceConfiguration,
    Network,
    NetworkConnection,
    Image,
)
from dashboard.exceptions import (
    InvalidVlanConfigurationException,
    NetworkExistsException,
    ResourceAvailabilityException
)

import logging
logger = logging.getLogger(__name__)


class Define_Hardware(WorkflowStep):

    template = 'resource/steps/define_hardware.html'
    title = "Define Hardware"
    description = "Choose the type and amount of machines you want"
    short_title = "hosts"

    def __init__(self, *args, **kwargs):
        self.form = None
        super().__init__(*args, **kwargs)

    def get_context(self):
        context = super(Define_Hardware, self).get_context()
        user = self.repo_get(self.repo.SESSION_USER)
        context['form'] = self.form or HardwareDefinitionForm(user)
        return context

    def update_models(self, data):
        data = data['filter_field']
        models = self.repo_get(self.repo.RESOURCE_TEMPLATE_MODELS, {})
        models['resources'] = []  # This will always clear existing data when this step changes
        models['connections'] = []
        models['interfaces'] = {}
        if "template" not in models:
            template = ResourceTemplate.objects.create(temporary=True)
            models['template'] = template

        resource_data = data['resource']

        new_template = models['template']

        public_network = Network.objects.create(name="public", bundle=new_template, is_public=True)

        all_networks = {public_network.id: public_network}

        for resource_template_dict in resource_data.values():
            id = resource_template_dict['id']
            old_template = ResourceTemplate.objects.get(id=id)

            # instantiate genericHost and store in repo
            for _ in range(0, resource_template_dict['count']):
                resource_configs = old_template.resourceConfigurations.all()
                for config in resource_configs:
                    # need to save now for connections to refer to it later
                    new_config = ResourceConfiguration.objects.create(
                        profile=config.profile,
                        image=config.image,
                        name=config.name,
                        template=new_template)

                    for interface_config in config.interface_configs.all():
                        new_interface_config = InterfaceConfiguration.objects.create(
                            profile=interface_config.profile,
                            resource_config=new_config)

                        for connection in interface_config.connections.all():
                            network = None
                            if connection.network.is_public:
                                network = public_network
                            else:
                                # check if network is known
                                if connection.network.id not in all_networks:
                                    # create matching one
                                    new_network = Network(
                                        name=connection.network.name + "_" + str(new_config.id),
                                        bundle=new_template,
                                        is_public=False)
                                    new_network.save()

                                    all_networks[connection.network.id] = new_network

                                network = all_networks[connection.network.id]

                            new_connection = NetworkConnection(
                                network=network,
                                vlan_is_tagged=connection.vlan_is_tagged)

                            new_interface_config.save()  # can't do later because M2M on next line
                            new_connection.save()

                            new_interface_config.connections.add(new_connection)

                        unique_resource_ref = new_config.name + "_" + str(new_config.id)
                        if unique_resource_ref not in models['interfaces']:
                            models['interfaces'][unique_resource_ref] = []
                        models['interfaces'][unique_resource_ref].append(interface_config)

                    models['resources'].append(new_config)

            models['networks'] = all_networks

        # add selected lab to models
        for lab_dict in data['lab'].values():
            if lab_dict['selected']:
                models['template'].lab = Lab.objects.get(lab_user__id=lab_dict['id'])
                models['template'].save()
                break  # if somehow we get two 'true' labs, we only use one

        # return to repo
        self.repo_put(self.repo.RESOURCE_TEMPLATE_MODELS, models)

    def update_confirmation(self):
        confirm = self.repo_get(self.repo.CONFIRMATION, {})
        if "template" not in confirm:
            confirm['template'] = {}
        confirm['template']['resources'] = []
        models = self.repo_get(self.repo.RESOURCE_TEMPLATE_MODELS, {})
        if 'template' in models:
            for resource in models['template'].getConfigs():
                host_dict = {"name": resource.name, "profile": resource.profile.name}
                confirm['template']['resources'].append(host_dict)
        if "template" in models:
            confirm['template']['lab'] = models['template'].lab.lab_user.username
        self.repo_put(self.repo.CONFIRMATION, confirm)

    def post(self, post_data, user):
        try:
            user = self.repo_get(self.repo.SESSION_USER)
            self.form = HardwareDefinitionForm(user, post_data)
            if self.form.is_valid():
                self.update_models(self.form.cleaned_data)
                self.update_confirmation()
                self.set_valid("Step Completed")
            else:
                self.set_invalid("Please complete the fields highlighted in red to continue")
        except Exception as e:
            print("Caught exception: " + str(e))
            traceback.print_exc()
            self.form = None
            self.set_invalid("Please select a lab.")


class Define_Software(WorkflowStep):
    template = 'config_bundle/steps/define_software.html'
    title = "Pick Software"
    description = "Choose the opnfv and image of your machines"
    short_title = "host config"

    def build_filter_data(self, hosts_data):
        """
        Build list of Images to filter out.

        returns a 2D array of images to exclude
        based on the ordering of the passed
        hosts_data
        """

        filter_data = []
        user = self.repo_get(self.repo.SESSION_USER)
        lab = self.repo_get(self.repo.RESOURCE_TEMPLATE_MODELS)['template'].lab
        for i, host_data in enumerate(hosts_data):
            host = ResourceConfiguration.objects.get(pk=host_data['host_id'])
            wrong_owner = Image.objects.exclude(owner=user).exclude(public=True)
            wrong_host = Image.objects.exclude(architecture=host.profile.architecture)
            wrong_lab = Image.objects.exclude(from_lab=lab)
            excluded_images = wrong_owner | wrong_host | wrong_lab
            filter_data.append([])
            for image in excluded_images:
                filter_data[i].append(image.pk)
        return filter_data

    def create_hostformset(self, hostlist, data=None):
        hosts_initial = []
        configs = self.repo_get(self.repo.RESOURCE_TEMPLATE_MODELS, {}).get("resources")
        if configs:
            for i in range(len(configs)):
                default_name = 'laas-node'
                if i > 0:
                    default_name = default_name + "-" + str(i + 1)
                hosts_initial.append({
                    'host_id': configs[i].id,
                    'host_name': default_name,
                    'headnode': False,
                    'image': configs[i].image
                })
        else:
            for host in hostlist:
                hosts_initial.append({
                    'host_id': host.id,
                    'host_name': host.name
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
        return self.repo_get(self.repo.RESOURCE_TEMPLATE_MODELS).get("resources")

    def get_context(self):
        context = super(Define_Software, self).get_context()

        context["formset"] = self.create_hostformset(self.get_host_list())

        return context

    def post(self, post_data, user):
        hosts = self.get_host_list()
        formset = self.create_hostformset(hosts, data=post_data)
        has_headnode = False
        if formset.is_valid():
            for i, form in enumerate(formset):
                host = hosts[i]
                image = form.cleaned_data['image']
                hostname = form.cleaned_data['host_name']
                headnode = form.cleaned_data['headnode']
                if headnode:
                    has_headnode = True
                host.is_head_node = headnode
                host.name = hostname
                host.image = image
                # RFC921: They must start with a letter, end with a letter or digit and have only letters or digits or hyphen as interior characters
                if bool(re.match("^[A-Za-z0-9-]*$", hostname)) is False:
                    self.set_invalid("Device names must only contain alphanumeric characters and dashes.")
                    return
                if not hostname[0].isalpha() or not hostname[-1].isalnum():
                    self.set_invalid("Device names must start with a letter and end with a letter or digit.")
                    return
                for j in range(i):
                    if j != i and hostname == hosts[j].name:
                        self.set_invalid("Devices must have unique names. Please try again.")
                        return
                host.save()

            if not has_headnode and len(hosts) > 0:
                self.set_invalid("No headnode. Please set a headnode.")
                return

            self.set_valid("Completed")
        else:
            self.set_invalid("Please complete all fields.")


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
        models = self.repo_get(self.repo.RESOURCE_TEMPLATE_MODELS, {})
        if "bundle" not in models:
            return None
        lab = models['bundle'].lab
        if lab is None or lab.vlan_manager is None:
            return None
        try:
            vlans = lab.vlan_manager.get_vlans(count=lab.vlan_manager.block_size)
            self.repo_put(self.repo.VLANS, vlans)
            return vlans
        except Exception:
            return None

    def make_mx_network_dict(self, network):
        return {
            'id': network.id,
            'name': network.name,
            'public': network.is_public
        }

    def make_mx_resource_dict(self, resource_config):
        resource_dict = {
            'id': resource_config.id,
            'interfaces': [],
            'value': {
                'name': resource_config.name,
                'id': resource_config.id,
                'description': resource_config.profile.description
            }
        }

        for interface_config in resource_config.interface_configs.all():
            connections = []
            for connection in interface_config.connections.all():
                connections.append({'tagged': connection.vlan_is_tagged, 'network': connection.network.id})

            interface_dict = {
                "id": interface_config.id,
                "name": interface_config.profile.name,
                "description": "speed: " + str(interface_config.profile.speed) + "M\ntype: " + interface_config.profile.nic_type,
                "connections": connections
            }

            resource_dict['interfaces'].append(interface_dict)

        return resource_dict

    def make_mx_host_dict(self, generic_host):
        host = {
            'id': generic_host.profile.name,
            'interfaces': [],
            'value': {
                "name": generic_host.profile.name,
                "description": generic_host.profile.description
            }
        }
        for iface in generic_host.profile.interfaceprofile.all():
            host['interfaces'].append({
                "name": iface.name,
                "description": "speed: " + str(iface.speed) + "M\ntype: " + iface.nic_type
            })
        return host

    # first step guards this one, so can't get here without at least empty
    # models being populated by step one
    def get_context(self):
        context = super(Define_Nets, self).get_context()
        context.update({
            'form': NetworkDefinitionForm(),
            'debug': settings.DEBUG,
            'resources': {},
            'networks': {},
            'vlans': [],
            # remove others
            'hosts': [],
            'added_hosts': [],
            'removed_hosts': []
        })

        models = self.repo_get(self.repo.RESOURCE_TEMPLATE_MODELS)  # infallible, guarded by prior step
        for resource in models['resources']:
            d = self.make_mx_resource_dict(resource)
            context['resources'][d['id']] = d

        for network in models['networks'].values():
            d = self.make_mx_network_dict(network)
            context['networks'][d['id']] = d

        return context

    def post(self, post_data, user):
        try:
            xmlData = post_data.get("xml")
            self.updateModels(xmlData)
            # update model with xml
            self.set_valid("Networks applied successfully")
        except ResourceAvailabilityException:
            self.set_invalid("Public network not availble")
        except Exception as e:
            traceback.print_exc()
            self.set_invalid("An error occurred when applying networks: " + str(e))

    def resetNetworks(self, networks: List[Network]):  # potentially just pass template here?
        for network in networks:
            network.delete()

    def updateModels(self, xmlData):
        models = self.repo_get(self.repo.RESOURCE_TEMPLATE_MODELS, {})
        given_hosts = None
        interfaces = None
        networks = None
        try:
            given_hosts, interfaces, networks = self.parseXml(xmlData)
        except Exception as e:
            print("tried to parse Xml, got exception instead:")
            print(e)

        existing_rconfig_list = models.get("resources", [])
        existing_rconfigs = {}  # maps id to host
        for rconfig in existing_rconfig_list:
            existing_rconfigs["host_" + str(rconfig.id)] = rconfig

        bundle = models.get("template")  # hard fail if not in repo

        self.resetNetworks(models['networks'].values())
        models['networks'] = {}

        for net_id, net in networks.items():
            network = Network.objects.create(
                name=net['name'],
                bundle=bundle,
                is_public=net['public'])

            models['networks'][net_id] = network
            network.save()

        for hostid, given_host in given_hosts.items():
            for ifaceId in given_host['interfaces']:
                iface = interfaces[ifaceId]

                iface_config = InterfaceConfiguration.objects.get(id=iface['config_id'])
                if iface_config.resource_config.template.id != bundle.id:
                    raise ValidationError("User does not own the template they are editing")

                for connection in iface['connections']:
                    network_id = connection['network']
                    net = models['networks'][network_id]
                    connection = NetworkConnection(vlan_is_tagged=connection['tagged'], network=net)
                    connection.save()
                    iface_config.connections.add(connection)
                    iface_config.save()
        self.repo_put(self.repo.RESOURCE_TEMPLATE_MODELS, models)

    def decomposeXml(self, xmlString):
        """
        Translate XML into useable data.

        This function takes in an xml doc from our front end
        and returns dictionaries that map cellIds to the xml
        nodes themselves. There is no unpacking of the
        xml objects, just grouping and organizing
        """
        connections = {}
        networks = {}
        hosts = {}
        interfaces = {}
        network_ports = {}

        xmlDom = minidom.parseString(xmlString)
        root = xmlDom.documentElement.firstChild
        for cell in root.childNodes:
            cellId = cell.getAttribute('id')
            group = cellId.split("_")[0]
            parentGroup = cell.getAttribute("parent").split("_")[0]
            # place cell into correct group

            if cell.getAttribute("edge"):
                connections[cellId] = cell

            elif "network" in group:
                networks[cellId] = cell

            elif "host" in group:
                hosts[cellId] = cell

            elif "host" in parentGroup:
                interfaces[cellId] = cell

            # make network ports also map to thier network
            elif "network" in parentGroup:
                network_ports[cellId] = cell.getAttribute("parent")  # maps port ID to net ID

        return connections, networks, hosts, interfaces, network_ports

    # serialize and deserialize xml from mxGraph
    def parseXml(self, xmlString):
        networks = {}  # maps net name to network object
        hosts = {}  # cotains id -> hosts, each containing interfaces, referencing networks
        interfaces = {}  # maps id -> interface
        untagged_ifaces = set()  # used to check vlan config
        network_names = set()  # used to check network names
        xml_connections, xml_nets, xml_hosts, xml_ifaces, xml_ports = self.decomposeXml(xmlString)

        # parse Hosts
        for cellId, cell in xml_hosts.items():
            cell_json_str = cell.getAttribute("value")
            cell_json = json.loads(cell_json_str)
            host = {"interfaces": [], "name": cellId, "hostname": cell_json['name']}
            hosts[cellId] = host

        # parse networks
        for cellId, cell in xml_nets.items():
            escaped_json_str = cell.getAttribute("value")
            json_str = escaped_json_str.replace('&quot;', '"')
            net_info = json.loads(json_str)
            net_name = net_info['name']
            public = net_info['public']
            if net_name in network_names:
                raise NetworkExistsException("Non unique network name found")
            network = {"name": net_name, "public": public, "id": cellId}
            networks[cellId] = network
            network_names.add(net_name)

        # parse interfaces
        for cellId, cell in xml_ifaces.items():
            parentId = cell.getAttribute('parent')
            cell_json_str = cell.getAttribute("value")
            cell_json = json.loads(cell_json_str)
            iface = {"graph_id": cellId, "connections": [], "config_id": cell_json['id'], "profile_name": cell_json['name']}
            hosts[parentId]['interfaces'].append(cellId)
            interfaces[cellId] = iface

        # parse connections
        for cellId, cell in xml_connections.items():
            escaped_json_str = cell.getAttribute("value")
            json_str = escaped_json_str.replace('&quot;', '"')
            attributes = json.loads(json_str)
            tagged = attributes['tagged']
            interface = None
            network = None
            src = cell.getAttribute("source")
            tgt = cell.getAttribute("target")
            if src in interfaces:
                interface = interfaces[src]
                network = networks[xml_ports[tgt]]
            else:
                interface = interfaces[tgt]
                network = networks[xml_ports[src]]

            if not tagged:
                if interface['config_id'] in untagged_ifaces:
                    raise InvalidVlanConfigurationException("More than one untagged vlan on an interface")
                untagged_ifaces.add(interface['config_id'])

            # add connection to interface
            interface['connections'].append({"tagged": tagged, "network": network['id']})

        return hosts, interfaces, networks


class Resource_Meta_Info(WorkflowStep):
    template = 'resource/steps/meta_info.html'
    title = "Extra Info"
    description = "Please fill out the rest of the information about your resource"
    short_title = "pod info"

    def update_confirmation(self):
        confirm = self.repo_get(self.repo.CONFIRMATION, {})
        if "template" not in confirm:
            confirm['template'] = {}
        models = self.repo_get(self.repo.RESOURCE_TEMPLATE_MODELS, {})
        if "template" in models:
            confirm['template']['description'] = models['template'].description
            confirm['template']['name'] = models['template'].name
        self.repo_put(self.repo.CONFIRMATION, confirm)

    def get_context(self):
        context = super(Resource_Meta_Info, self).get_context()
        name = ""
        desc = ""
        models = self.repo_get(self.repo.RESOURCE_TEMPLATE_MODELS, None)
        bundle = models['template']
        if bundle:
            name = bundle.name
            desc = bundle.description
        context['form'] = ResourceMetaForm(initial={"bundle_name": name, "bundle_description": desc})
        return context

    def post(self, post_data, user):
        form = ResourceMetaForm(post_data)
        if form.is_valid():
            models = self.repo_get(self.repo.RESOURCE_TEMPLATE_MODELS, {})
            name = form.cleaned_data['bundle_name']
            desc = form.cleaned_data['bundle_description']
            bundle = models['template']  # infallible
            bundle.name = name
            bundle.description = desc
            bundle.save()
            self.repo_put(self.repo.RESOURCE_TEMPLATE_MODELS, models)
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
            self.set_valid("Step Completed")
        else:
            self.set_invalid("Please complete all fields.")
