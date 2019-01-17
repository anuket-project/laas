##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


import django.forms as forms
from django.forms import widgets
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.forms.widgets import NumberInput

from account.models import Lab
from account.models import UserProfile
from resource_inventory.models import (
    GenericResourceBundle,
    ConfigBundle,
    OPNFVRole,
    Image,
    Installer,
    Scenario
)


class SearchableSelectMultipleWidget(widgets.SelectMultiple):
    template_name = 'dashboard/searchable_select_multiple.html'

    def __init__(self, attrs=None):
        self.items = attrs['set']
        self.show_from_noentry = attrs['show_from_noentry']
        self.show_x_results = attrs['show_x_results']
        self.results_scrollable = attrs['scrollable']
        self.selectable_limit = attrs['selectable_limit']
        self.placeholder = attrs['placeholder']
        self.name = attrs['name']
        self.initial = attrs.get("initial", "")
        self.default_entry = attrs.get("default_entry", "")
        self.edit = attrs.get("edit", False)
        self.wf_type = attrs.get("wf_type")
        self.incompatible = attrs.get("incompatible", "false")

        super(SearchableSelectMultipleWidget, self).__init__(attrs)

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
            'default_entry': self.default_entry,
            'edit': self.edit,
            'wf_type': self.wf_type,
            'incompatible': self.incompatible
        }


class ResourceSelectorForm(forms.Form):

    def __init__(self, data=None, **kwargs):
        chosen_resource = ""
        bundle = None
        edit = False
        if "chosen_resource" in kwargs:
            chosen_resource = kwargs.pop("chosen_resource")
        if "bundle" in kwargs:
            bundle = kwargs.pop("bundle")
        if "edit" in kwargs:
            edit = kwargs.pop("edit")
        super(ResourceSelectorForm, self).__init__(data=data, **kwargs)
        queryset = GenericResourceBundle.objects.select_related("owner").all()
        if data and 'user' in data:
            queryset = queryset.filter(owner=data['user'])

        attrs = self.build_search_widget_attrs(chosen_resource, bundle, edit, queryset)

        self.fields['generic_resource_bundle'] = forms.CharField(
            widget=SearchableSelectMultipleWidget(attrs=attrs)
        )

    def build_search_widget_attrs(self, chosen_resource, bundle, edit, queryset):
        resources = {}
        for res in queryset:
            displayable = {}
            displayable['small_name'] = res.name
            if res.owner:
                displayable['expanded_name'] = res.owner.username
            else:
                displayable['expanded_name'] = ""
            displayable['string'] = res.description
            displayable['id'] = res.id
            resources[res.id] = displayable

        attrs = {
            'set': resources,
            'show_from_noentry': "true",
            'show_x_results': -1,
            'scrollable': "true",
            'selectable_limit': 1,
            'name': "generic_resource_bundle",
            'placeholder': "resource",
            'initial': chosen_resource,
            'edit': edit,
            'wf_type': 1
        }
        return attrs


class SWConfigSelectorForm(forms.Form):

    def __init__(self, *args, **kwargs):
        chosen_software = ""
        bundle = None
        edit = False
        resource = None
        if "chosen_software" in kwargs:
            chosen_software = kwargs.pop("chosen_software")

        if "bundle" in kwargs:
            bundle = kwargs.pop("bundle")
        if "edit" in kwargs:
            edit = kwargs.pop("edit")
        if "resource" in kwargs:
            resource = kwargs.pop("resource")
        super(SWConfigSelectorForm, self).__init__(*args, **kwargs)
        attrs = self.build_search_widget_attrs(chosen_software, bundle, edit, resource)
        self.fields['software_bundle'] = forms.CharField(
            widget=SearchableSelectMultipleWidget(attrs=attrs)
        )

    def build_search_widget_attrs(self, chosen, bundle, edit, resource):
        configs = {}
        queryset = ConfigBundle.objects.select_related('owner').all()
        if resource:
            queryset = queryset.filter(bundle=resource)

        for config in queryset:
            displayable = {}
            displayable['small_name'] = config.name
            displayable['expanded_name'] = config.owner.username
            displayable['string'] = config.description
            displayable['id'] = config.id
            configs[config.id] = displayable

        incompatible_choice = "false"
        if bundle and bundle.id not in configs:
            displayable = {}
            displayable['small_name'] = bundle.name
            displayable['expanded_name'] = bundle.owner.username
            displayable['string'] = bundle.description
            displayable['id'] = bundle.id
            configs[bundle.id] = displayable
            incompatible_choice = "true"

        attrs = {
            'set': configs,
            'show_from_noentry': "true",
            'show_x_results': -1,
            'scrollable': "true",
            'selectable_limit': 1,
            'name': "software_bundle",
            'placeholder': "config",
            'initial': chosen,
            'edit': edit,
            'wf_type': 2,
            'incompatible': incompatible_choice
        }
        return attrs


class BookingMetaForm(forms.Form):

    length = forms.IntegerField(
        widget=NumberInput(
            attrs={
                "type": "range",
                'min': "0",
                "max": "21",
                "value": "0"
            }
        )
    )
    purpose = forms.CharField(max_length=1000)
    project = forms.CharField(max_length=400)
    info_file = forms.CharField(max_length=1000, required=False)

    def __init__(self, data=None, *args, **kwargs):
        chosen_users = []
        if "default_user" in kwargs:
            default_user = kwargs.pop("default_user")
        else:
            default_user = "you"
        self.default_user = default_user
        if "chosen_users" in kwargs:
            chosen_users = kwargs.pop("chosen_users")
        elif data and "users" in data:
            chosen_users = data.getlist("users")
        else:
            pass

        super(BookingMetaForm, self).__init__(data=data, **kwargs)

        self.fields['users'] = forms.CharField(
            widget=SearchableSelectMultipleWidget(
                attrs=self.build_search_widget_attrs(chosen_users, default_user=default_user)
            ),
            required=False
        )

    def build_user_list(self):
        """
        returns a mapping of UserProfile ids to displayable objects expected by
        searchable multiple select widget
        """
        try:
            users = {}
            d_qset = UserProfile.objects.select_related('user').all().exclude(user__username=self.default_user)
            for userprofile in d_qset:
                user = {
                    'id': userprofile.user.id,
                    'expanded_name': userprofile.full_name,
                    'small_name': userprofile.user.username,
                    'string': userprofile.email_addr
                }

                users[userprofile.user.id] = user

            return users
        except Exception:
            pass

    def build_search_widget_attrs(self, chosen_users, default_user="you"):

        attrs = {
            'set': self.build_user_list(),
            'show_from_noentry': "false",
            'show_x_results': 10,
            'scrollable': "false",
            'selectable_limit': -1,
            'name': "users",
            'placeholder': "username",
            'initial': chosen_users,
            'edit': False
        }
        return attrs


class MultipleSelectFilterWidget(forms.Widget):
    def __init__(self, attrs=None):
        super(MultipleSelectFilterWidget, self).__init__(attrs)
        self.attrs = attrs
        self.template_name = "dashboard/multiple_select_filter_widget.html"

    def render(self, name, value, attrs=None, renderer=None):
        attrs = self.attrs
        self.context = self.get_context(name, value, attrs)
        html = render_to_string(self.template_name, context=self.context)
        return mark_safe(html)

    def get_context(self, name, value, attrs):
        return attrs


class MultipleSelectFilterField(forms.Field):

    def __init__(self, required=True, widget=None, label=None, initial=None,
                 help_text='', error_messages=None, show_hidden_initial=False,
                 validators=(), localize=False, disabled=False, label_suffix=None):
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
        # this is bad, but django forms are annoying
        self.widget = widget
        if self.widget is None:
            self.widget = MultipleSelectFilterWidget()
        super(MultipleSelectFilterField, self).__init__(
            required=required,
            widget=self.widget,
            label=label,
            initial=None,
            help_text=help_text,
            error_messages=error_messages,
            show_hidden_initial=show_hidden_initial,
            validators=validators,
            localize=localize,
            disabled=disabled,
            label_suffix=label_suffix
        )

        def clean(data):
            """
            This method will raise a django.forms.ValidationError or return clean data
            """
            return data


class FormUtils:
    @staticmethod
    def getLabData(multiple_selectable_hosts):
        """
        Gets all labs and thier host profiles and returns a serialized version the form can understand.
        Should be rewritten with a related query to make it faster
        Should be moved outside of global scope
        """
        labs = {}
        hosts = {}
        items = {}
        mapping = {}
        for lab in Lab.objects.all():
            slab = {}
            slab['id'] = "lab_" + str(lab.lab_user.id)
            slab['name'] = lab.name
            slab['description'] = lab.description
            slab['selected'] = 0
            slab['selectable'] = 1
            slab['follow'] = 1
            slab['multiple'] = 0
            items[slab['id']] = slab
            mapping[slab['id']] = []
            labs[slab['id']] = slab
            for host in lab.hostprofiles.all():
                shost = {}
                shost['forms'] = [{"name": "host_name", "type": "text", "placeholder": "hostname"}]
                shost['id'] = "host_" + str(host.id)
                shost['name'] = host.name
                shost['description'] = host.description
                shost['selected'] = 0
                shost['selectable'] = 1
                shost['follow'] = 0
                shost['multiple'] = multiple_selectable_hosts
                items[shost['id']] = shost
                mapping[slab['id']].append(shost['id'])
                if shost['id'] not in mapping:
                    mapping[shost['id']] = []
                mapping[shost['id']].append(slab['id'])
                hosts[shost['id']] = shost

        filter_objects = [("labs", labs.values()), ("hosts", hosts.values())]

        context = {
            'filter_objects': filter_objects,
            'mapping': mapping,
            'filter_items': items
        }
        return context


class HardwareDefinitionForm(forms.Form):

    def __init__(self, *args, **kwargs):
        selection_data = kwargs.pop("selection_data", False)
        super(HardwareDefinitionForm, self).__init__(*args, **kwargs)
        attrs = FormUtils.getLabData(1)
        attrs['selection_data'] = selection_data
        self.fields['filter_field'] = MultipleSelectFilterField(
            widget=MultipleSelectFilterWidget(
                attrs=attrs
            )
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
    fields = ["host_name", "role", "image"]

    host_name = forms.CharField(max_length=200, disabled=True, required=False)
    role = forms.ModelChoiceField(queryset=OPNFVRole.objects.all())
    image = forms.ModelChoiceField(queryset=Image.objects.all())


class SoftwareConfigurationForm(forms.Form):

    name = forms.CharField(max_length=200)
    description = forms.CharField(widget=forms.Textarea)
    opnfv = forms.BooleanField(disabled=True, required=False)
    installer = forms.ModelChoiceField(queryset=Installer.objects.all(), disabled=True, required=False)
    scenario = forms.ModelChoiceField(queryset=Scenario.objects.all(), disabled=True, required=False)


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


class SnapshotMetaForm(forms.Form):
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
