##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.contrib import admin

from resource_inventory.models import *

profiles = [HostProfile, InterfaceProfile, DiskProfile, CpuProfile, RamProfile]

admin.site.register(profiles)

generics = [GenericResourceBundle, GenericResource, GenericHost, GenericPod, GenericInterface]

admin.site.register(generics)

physical = [Host, Interface, Network, Vlan, ResourceBundle]

admin.site.register(physical)

config = [Scenario, Installer, Opsys, ConfigBundle, OPNFVConfig, OPNFVRole, Image, HostConfiguration]

admin.site.register(config)
