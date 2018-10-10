##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from rest_framework import serializers

from resource_inventory.models import *

class BookingField(serializers.Field):

    def to_representation(self, booking):
        """
        Takes in a booking object.
        Returns a dictionary of primitives representing that booking
        """
        ser = {}
        ser['id'] = booking.id
        # main loop to grab relevant info out of booking
        host_configs = {}  # mapping hostname -> config
        networks = {}  # mapping vlan id -> network_hosts
        for host in booking.resource.hosts.all():
            host_configs[host.name] = HostConfiguration.objects.get(host=host.template)
            if "jumphost" not in ser and host_configs[host.name].opnfvRole.name.lower() == "jumphost":
                ser['jumphost'] = host.name
            #host is a Host model
            for i in range(len(host.interfaces.all())):
                interface = host.interfaces.all()[i]
                #interface is an Interface model
                for vlan in interface.config.all():
                    #vlan is Vlan model
                    if vlan.id not in networks:
                        networks[vlan.id] = []
                    net_host = {"hostname": host.name, "tagged": vlan.tagged, "interface":i}
                    networks[vlan.id].append(net_host)
        #creates networking object of proper form
        networking = []
        for vlanid in networks:
            network = {}
            network['vlan_id'] = vlanid
            network['hosts'] = networks[vlanid]

        ser['networking'] = networking

        #creates hosts object of correct form
        hosts = []
        for hostname in host_configs:
            host = {"hostname": hostname}
            host['deploy_image'] = True  # TODO?
            image = host_configs[hostname].image
            host['image'] = {
                "name": image.name,
                "lab_id": image.lab_id,
                "dashboard_id": image.id
            }
            hosts.append(host)

        ser['hosts'] = hosts

        return ser

    def to_internal_value(self, data):
        """
        Takes in a dictionary of primitives
        Returns a booking object

        This is not going to be implemented or allowed.
        If someone needs to create a booking through the api,
        they will send a different booking object
        """
        return None

class BookingSerializer(serializers.Serializer):

    booking = BookingField()

#Host Type stuff, for inventory

class CPUSerializer(serializers.ModelSerializer):
    class Meta:
        model = CpuProfile
        fields = ('cores', 'architecture', 'cpus')

class DiskSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiskProfile
        fields = ('size', 'media_type', 'name')

class InterfaceProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterfaceProfile
        fields = ('speed', 'name')

class RamSerializer(serializers.ModelSerializer):
    class Meta:
        model = RamProfile
        fields = ('amount', 'channels')

class HostTypeSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    ram = RamSerializer()
    interface = InterfaceProfileSerializer()
    description = serializers.CharField(max_length=1000)
    disks = DiskSerializer()
    cpu = CPUSerializer()

#the rest of the inventory stuff
class NetworkSerializer(serializers.Serializer):
    cidr = serializers.CharField(max_length=200)
    gateway = serializers.IPAddressField(max_length=200)
    vlan = serializers.IntegerField()

class ImageSerializer(serializers.ModelSerializer):
    lab_id = serializers.IntegerField()
    id = serializers.IntegerField(source="dashboard_id")
    name = serializers.CharField(max_length=50)
    description = serializers.CharField(max_length=200)
    class Meta:
        model = Image

class InterfaceField(serializers.Field):
    def to_representation(self, interface):
        pass

    def to_internal_value(self, data):
        """
        takes in a serialized interface and creates an Interface model
        """
        mac = data['mac']
        bus_address = data['busaddr']
        switch_name = data['switchport']['switch_name']
        port_name = data['switchport']['port_name']
        # TODO config??
        return Interface.objects.create(
            mac_address=mac,
            bus_address=bus_address,
            switch_name=switch_name,
            port_name=port_name
        )

class InventoryHostSerializer(serializers.Serializer):
    hostname = serializers.CharField(max_length=100)
    host_type = serializers.CharField(max_length=100)
    interfaces = InterfaceField()


class InventorySerializer(serializers.Serializer):
    hosts = InventoryHostSerializer()
    networks = NetworkSerializer()
    images = ImageSerializer()
    host_types = HostTypeSerializer()
