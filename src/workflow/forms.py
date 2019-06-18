##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


import django.forms as forms
from django.forms import widgets, ValidationError
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.forms.widgets import NumberInput

import json

from account.models import Lab
from account.models import UserProfile
from resource_inventory.models import (
    OPNFVRole,
    Installer,
    Scenario,
)
from booking.lib import get_user_items, get_user_field_opts


class SearchableSelectMultipleWidget(widgets.SelectMultiple):
    template_name = 'dashboard/searchable_select_multiple.html'

    def __init__(self, attrs=None):
        self.items = attrs['items']
        self.show_from_noentry = attrs['show_from_noentry']
        self.show_x_results = attrs['show_x_results']
        self.results_scrollable = attrs['results_scrollable']
        self.selectable_limit = attrs['selectable_limit']
        self.placeholder = attrs['placeholder']
        self.name = attrs['name']
        self.initial = attrs.get("initial", [])

        super(SearchableSelectMultipleWidget, self).__init__()

    def render(self, name, value, attrs=None, renderer=None):

        context = self.get_context(attrs)
        return mark_safe(render_to_string(self.template_name, context))

    def get_context(self, attrs):
        return {
            'items': self.items,
            'name': self.name,
            'show_from_noentry': self.show_from_noentry,
            'show_x_results': self.show_x_results,
            'results_scrollable': self.results_scrollable,
            'selectable_limit': self.selectable_limit,
            'placeholder': self.placeholder,
            'initial': self.initial,
        }


class SearchableSelectMultipleField(forms.Field):
    def __init__(self, *args, required=True, widget=None, label=None, disabled=False,
                 items=None, queryset=None, show_from_noentry=True, show_x_results=-1,
                 results_scrollable=False, selectable_limit=-1, placeholder="search here",
                 name="searchable_select", initial=[], **kwargs):
        """from the documentation:
        # required -- Boolean that specifies whether the field is required.
        #             True by default.
        # widget -- A Widget class, or instance of a Widget class, that should
        #           be used for this Field when displaying it. Each Field has a
        #           default Widget that it'll use if you don't specify this. In
        #           most cases, the default widget is TextInput.
        # label -- A verbose name for this field, for use in displaying this
        #          field in a form. By default, Django will use a "pretty"
        #          version of the form field name, if the Field is part of a
        #          Form.
        # initial -- A value to use in this Field's initial display. This value
        #            is *not* used as a fallback if data isn't given.
        # help_text -- An optional string to use as "help text" for this Field.
        # error_messages -- An optional dictionary to override the default
        #                   messages that the field will raise.
        # show_hidden_initial -- Boolean that specifies if it is needed to render a
        #                        hidden widget with initial value after widget.
        # validators -- List of additional validators to use
        # localize -- Boolean that specifies if the field should be localized.
        # disabled -- Boolean that specifies whether the field is disabled, that
        #             is its widget is shown in the form but not editable.
        # label_suffix -- Suffix to be added to the label. Overrides
        #                 form's label_suffix.
        """

        self.widget = widget
        if self.widget is None:
            self.widget = SearchableSelectMultipleWidget(
                attrs={
                    'items': items,
                    'initial': [obj.id for obj in initial],
                    'show_from_noentry': show_from_noentry,
                    'show_x_results': show_x_results,
                    'results_scrollable': results_scrollable,
                    'selectable_limit': selectable_limit,
                    'placeholder': placeholder,
                    'name': name,
                    'disabled': disabled
                }
            )
        self.disabled = disabled
        self.queryset = queryset
        self.selectable_limit = selectable_limit

        super().__init__(disabled=disabled, **kwargs)

        self.required = required

    def clean(self, data):
        data = data[0]
        if not data:
            if self.required:
                raise ValidationError("Nothing was selected")
            else:
                return []
        data_as_list = json.loads(data)
        if self.selectable_limit != -1:
            if len(data_as_list) > self.selectable_limit:
                raise ValidationError("Too many items were selected")

        items = []
        for elem in data_as_list:
            items.append(self.queryset.get(id=elem))

        return items


class SearchableSelectAbstractForm(forms.Form):
    def __init__(self, *args, queryset=None, initial=[], **kwargs):
        self.queryset = queryset
        items = self.generate_items(self.queryset)
        options = self.generate_options()

        super(SearchableSelectAbstractForm, self).__init__(*args, **kwargs)
        self.fields['searchable_select'] = SearchableSelectMultipleField(
            initial=initial,
            items=items,
            queryset=self.queryset,
            **options
        )

    def get_validated_bundle(self):
        bundles = self.cleaned_data['searchable_select']
        if len(bundles) < 1:  # don't need to check for >1, as field does that for us
            raise ValidationError("No bundle was selected")
        return bundles[0]

    def generate_items(self, queryset):
        raise Exception("SearchableSelectAbstractForm does not implement concrete generate_items()")

    def generate_options(self, disabled=False):
        return {
            'show_from_noentry': True,
            'show_x_results': -1,
            'results_scrollable': True,
            'selectable_limit': 1,
            'placeholder': 'Search for a Bundle',
            'name': 'searchable_select',
            'disabled': False
        }


class SWConfigSelectorForm(SearchableSelectAbstractForm):
    def generate_items(self, queryset):
        items = {}

        for bundle in queryset:
            items[bundle.id] = {
                'expanded_name': bundle.name,
                'small_name': bundle.owner.username,
                'string': bundle.description,
                'id': bundle.id
            }

        return items


class OPNFVSelectForm(SearchableSelectAbstractForm):
    def generate_items(self, queryset):
        items = {}

        for config in queryset:
            items[config.id] = {
                'expanded_name': config.name,
                'small_name': config.bundle.owner.username,
                'string': config.description,
                'id': config.id
            }

        return items


class ResourceSelectorForm(SearchableSelectAbstractForm):
    def generate_items(self, queryset):
        items = {}

        for bundle in queryset:
            items[bundle.id] = {
                'expanded_name': bundle.name,
                'small_name': bundle.owner.username,
                'string': bundle.description,
                'id': bundle.id
            }

        return items


class BookingMetaForm(forms.Form):

    length = forms.IntegerField(
        widget=NumberInput(
            attrs={
                "type": "range",
                'min': "1",
                "max": "21",
                "value": "1"
            }
        )
    )
    purpose = forms.CharField(max_length=1000)
    project = forms.CharField(max_length=400)
    info_file = forms.CharField(max_length=1000, required=False)
    deploy_opnfv = forms.BooleanField(required=False)

    def __init__(self, *args, user_initial=[], owner=None, **kwargs):
        super(BookingMetaForm, self).__init__(**kwargs)

        self.fields['users'] = SearchableSelectMultipleField(
            queryset=UserProfile.objects.select_related('user').exclude(user=owner),
            initial=user_initial,
            items=get_user_items(exclude=owner),
            required=False,
            **get_user_field_opts()
        )


class MultipleSelectFilterWidget(forms.Widget):
    def __init__(self, *args, display_objects=None, filter_items=None, neighbors=None, **kwargs):
        super(MultipleSelectFilterWidget, self).__init__(*args, **kwargs)
        self.display_objects = display_objects
        self.filter_items = filter_items
        self.neighbors = neighbors
        self.template_name = "dashboard/multiple_select_filter_widget.html"

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        html = render_to_string(self.template_name, context=context)
        return mark_safe(html)

    def get_context(self, name, value, attrs):
        return {
            'display_objects': self.display_objects,
            'neighbors': self.neighbors,
            'filter_items': self.filter_items,
            'initial_value': value
        }


class MultipleSelectFilterField(forms.Field):

    def __init__(self, **kwargs):
        self.initial = kwargs.get("initial")
        super().__init__(**kwargs)

    def to_python(self, value):
        return json.loads(value)


class FormUtils:
    @staticmethod
    def getLabData(multiple_hosts=False):
        """
        Gets all labs and thier host profiles and returns a serialized version the form can understand.
        Should be rewritten with a related query to make it faster
        """
        # javascript truthy variables
        true = 1
        false = 0
        if multiple_hosts:
            multiple_hosts = true
        else:
            multiple_hosts = false
        labs = {}
        hosts = {}
        items = {}
        neighbors = {}
        for lab in Lab.objects.all():
            lab_node = {
                'id': "lab_" + str(lab.lab_user.id),
                'model_id': lab.lab_user.id,
                'name': lab.name,
                'description': lab.description,
                'selected': false,
                'selectable': true,
                'follow': false,
                'multiple': false,
                'class': 'lab'
            }
            if multiple_hosts:
                # "follow" this lab node to discover more hosts if allowed
                lab_node['follow'] = true
            items[lab_node['id']] = lab_node
            neighbors[lab_node['id']] = []
            labs[lab_node['id']] = lab_node

            for host in lab.hostprofiles.all():
                host_node = {
                    'form': {"name": "host_name", "type": "text", "placeholder": "hostname"},
                    'id': "host_" + str(host.id),
                    'model_id': host.id,
                    'name': host.name,
                    'description': host.description,
                    'selected': false,
                    'selectable': true,
                    'follow': false,
                    'multiple': multiple_hosts,
                    'class': 'host'
                }
                if multiple_hosts:
                    host_node['values'] = []  # place to store multiple values
                items[host_node['id']] = host_node
                neighbors[lab_node['id']].append(host_node['id'])
                if host_node['id'] not in neighbors:
                    neighbors[host_node['id']] = []
                neighbors[host_node['id']].append(lab_node['id'])
                hosts[host_node['id']] = host_node

        display_objects = [("lab", labs.values()), ("host", hosts.values())]

        context = {
            'display_objects': display_objects,
            'neighbors': neighbors,
            'filter_items': items
        }
        return context


class HardwareDefinitionForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(HardwareDefinitionForm, self).__init__(*args, **kwargs)
        attrs = FormUtils.getLabData(multiple_hosts=True)
        self.fields['filter_field'] = MultipleSelectFilterField(
            widget=MultipleSelectFilterWidget(**attrs)
        )


class PodDefinitionForm(forms.Form):

    fields = ["xml"]
    xml = forms.CharField()


class ResourceMetaForm(forms.Form):

    bundle_name = forms.CharField(label="POD Name")
    bundle_description = forms.CharField(label="POD Description", widget=forms.Textarea)


class GenericHostMetaForm(forms.Form):

    host_profile = forms.CharField(label="Host Type", disabled=True, required=False)
    host_name = forms.CharField(label="Host Name")


class NetworkDefinitionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(NetworkDefinitionForm, self).__init__(**kwargs)


class NetworkConfigurationForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(NetworkConfigurationForm).__init__(**kwargs)


class HostSoftwareDefinitionForm(forms.Form):

    host_name = forms.CharField(max_length=200, disabled=True, required=False)
    headnode = forms.BooleanField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        imageQS = kwargs.pop("imageQS")
        super(HostSoftwareDefinitionForm, self).__init__(*args, **kwargs)
        self.fields['image'] = forms.ModelChoiceField(queryset=imageQS)


class WorkflowSelectionForm(forms.Form):
    fields = ['workflow']

    empty_permitted = False

    workflow = forms.ChoiceField(
        choices=(
            (0, 'Booking'),
            (1, 'Resource Bundle'),
            (2, 'Software Configuration')
        ),
        label="Choose Workflow",
        initial='booking',
        required=True
    )


class SnapshotHostSelectForm(forms.Form):
    host = forms.CharField()


class BasicMetaForm(forms.Form):
    name = forms.CharField()
    description = forms.CharField(widget=forms.Textarea)


class ConfirmationForm(forms.Form):
    fields = ['confirm']

    confirm = forms.ChoiceField(
        choices=(
            (True, "Confirm"),
            (False, "Cancel")
        )
    )


class OPNFVSelectionForm(forms.Form):
    installer = forms.ModelChoiceField(queryset=Installer.objects.all(), required=True)
    scenario = forms.ModelChoiceField(queryset=Scenario.objects.all(), required=True)


class OPNFVNetworkRoleForm(forms.Form):
    role = forms.CharField(max_length=200, disabled=True, required=False)

    def __init__(self, *args, config_bundle, **kwargs):
        super(OPNFVNetworkRoleForm, self).__init__(*args, **kwargs)
        self.fields['network'] = forms.ModelChoiceField(
            queryset=config_bundle.bundle.networks.all()
        )


class OPNFVHostRoleForm(forms.Form):
    host_name = forms.CharField(max_length=200, disabled=True, required=False)
    role = forms.ModelChoiceField(queryset=OPNFVRole.objects.all().order_by("name").distinct("name"))
