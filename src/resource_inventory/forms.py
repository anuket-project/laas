##############################################################################
# Copyright (c) 2020 Sawyer Bergeron, Sean Smith, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.core.exceptions import ValidationError
from django import forms

from resource_inventory.models import Network, InterfaceConfiguration


class InterfaceConfigurationForm(forms.ModelForm):
    class Meta:
        model = InterfaceConfiguration
        fields = ['profile', 'resource_config', 'connections']

    def clean(self):
        connections = self.cleaned_data.get('connections')
        resource_config = self.cleaned_data.get('resource_config')

        valid_nets = set(Network.objects.filter(bundle=resource_config.template))
        curr_nets = set([conn.network for conn in connections])

        if not curr_nets.issubset(valid_nets):
            raise ValidationError("Cannot have network connection to network outside pod")

        return self.cleaned_data
