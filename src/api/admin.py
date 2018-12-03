##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.apps import AppConfig
from django.contrib import admin

from api.models import (
    Job,
    OpnfvApiConfig,
    HardwareConfig,
    NetworkConfig,
    SoftwareConfig,
    AccessConfig,
    AccessRelation,
    SoftwareRelation,
    HostHardwareRelation,
    HostNetworkRelation,
)


class ApiConfig(AppConfig):
    name = 'apiJobs'


admin.site.register(Job)
admin.site.register(OpnfvApiConfig)
admin.site.register(HardwareConfig)
admin.site.register(NetworkConfig)
admin.site.register(SoftwareConfig)
admin.site.register(AccessConfig)
admin.site.register(AccessRelation)
admin.site.register(SoftwareRelation)
admin.site.register(HostHardwareRelation)
admin.site.register(HostNetworkRelation)
