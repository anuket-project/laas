##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.contrib import admin

from resource_inventory.forms import InterfaceConfigurationForm

from resource_inventory.models import (
    ResourceProfile,
    InterfaceProfile,
    DiskProfile,
    CpuProfile,
    RamProfile,
    ResourceTemplate,
    ResourceConfiguration,
    InterfaceConfiguration,
    Server,
    Interface,
    Network,
    Vlan,
    ResourceBundle,
    Scenario,
    Installer,
    Opsys,
    OPNFVConfig,
    OPNFVRole,
    Image,
    RemoteInfo,
    PhysicalNetwork,
    NetworkConnection,
)


admin.site.register([
    ResourceProfile,
    InterfaceProfile,
    DiskProfile,
    CpuProfile,
    RamProfile,
    ResourceTemplate,
    ResourceConfiguration,
    Server,
    Interface,
    Network,
    Vlan,
    ResourceBundle,
    Scenario,
    Installer,
    Opsys,
    OPNFVConfig,
    OPNFVRole,
    Image,
    PhysicalNetwork,
    NetworkConnection,
    RemoteInfo]
)


class InterfaceConfigurationAdmin(admin.ModelAdmin):
    form = InterfaceConfigurationForm


admin.site.register(InterfaceConfiguration, InterfaceConfigurationAdmin)
