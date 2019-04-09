##############################################################################
# Copyright (c) 2019 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.template.loader import render_to_string

from account.models import PublicNetwork

from resource_inventory.models import Vlan


class IDFTemplater:
    """
    Utility class to create a full IDF yaml file
    """
    def __init__(self):
        self.net_names = ["admin", "mgmt", "private", "public"]
        self.networks = {}
        for i, name in enumerate(self.net_names):
            self.networks[name] = {
                "name": name,
                "vlan": -1,
                "interface": i,
                "ip": "10.250." + str(i) + ".0",
                "netmask": 24
            }

    def makeIDF(self, booking):
        """
        fills the installer descriptor file template with info about the resource
        """
        template = "dashboard/idf.yaml"
        info = {}
        info['version'] = "0.1"
        info['net_config'] = self.get_net_config(booking)
        info['fuel'] = self.get_fuel_config(booking)

        return render_to_string(template, context=info)

    def get_net_config(self, booking):
        net_config = {}
        try:
            net_config['oob'] = self.get_oob_net(booking)
        except Exception:
            net_config['oob'] = {}
        try:
            net_config['public'] = self.get_public_net(booking)
        except Exception:
            net_config['public'] = {}

        for net in [net for net in self.net_names if net != "public"]:
            try:
                net_config[net] = self.get_single_net_config(booking, net)
            except Exception:
                net_config[net] = {}

        return net_config

    def get_public_net(self, booking):
        public = {}
        config = booking.opnfv_config
        public_role = config.networks.get(name="public")
        public_vlan = Vlan.objects.filter(network=public_role.network).first()
        public_network = PublicNetwork.objects.get(vlan=public_vlan.vlan_id, lab=booking.lab)
        self.networks['public']['vlan'] = public_vlan.vlan_id
        public['interface'] = self.networks['public']['interface']
        public['vlan'] = public_network.vlan  # untagged??
        public['network'] = public_network.cidr.split("/")[0]
        public['mask'] = public_network.cidr.split("/")[1]
        # public['ip_range'] = 4  # necesary?
        public['gateway'] = public_network.gateway
        public['dns'] = ["1.1.1.1", "8.8.8.8"]

        return public

    def get_oob_net(self, booking):
        net = {}
        hosts = booking.resource.hosts.all()
        addrs = [host.remote_management.address for host in hosts]
        net['ip_range'] = ",".join(addrs)
        net['vlan'] = "native"
        return net

    def get_single_net_config(self, booking, net_name):
        config = booking.opnfv_config
        role = config.networks.get(name=net_name)
        vlan = Vlan.objects.filter(network=role.network).first()
        self.networks[net_name]['vlan'] = vlan.vlan_id
        net = {}
        net['interface'] = self.networks[net_name]['interface']
        net['vlan'] = vlan.vlan_id
        net['network'] = self.networks[net_name]['ip']
        net['mask'] = self.networks[net_name]['netmask']

        return net

    def get_fuel_config(self, booking):
        fuel = {}
        fuel['jumphost'] = {}
        try:
            fuel['jumphost']['bridges'] = self.get_fuel_bridges()
        except Exception:
            fuel['jumphost']['bridges'] = {}

        fuel['network'] = {}
        try:
            fuel['network']['nodes'] = self.get_fuel_nodes(booking)
        except Exception:
            fuel['network']['nodes'] = {}

        return fuel

    def get_fuel_bridges(self):
        bridges = {}
        for net in self.net_names:
            bridges[net] = "br-" + net

        return bridges

    def get_fuel_nodes(self, booking):
        jumphost = booking.opnfv_config.host_opnfv_config.get(
            role__name__iexact="jumphost"
        )
        hosts = booking.resource.hosts.exclude(pk=jumphost.pk)
        nodes = []
        for host in hosts:
            node = {}
            ordered_interfaces = self.get_node_interfaces(host)
            node['interfaces'] = [iface['name'] for iface in ordered_interfaces]
            node['bus_addrs'] = [iface['bus'] for iface in ordered_interfaces]
            nodes.append(node)

        return nodes

    def get_node_interfaces(self, node):
        # TODO: this should sync with pdf ordering
        interfaces = []

        for iface in node.interfaces.all():
            interfaces.append({"name": iface.name, "bus": iface.bus_address})

        return interfaces
