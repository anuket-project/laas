##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
import django.forms as forms
from django.forms.widgets import NumberInput

from workflow.forms import (
    MultipleSelectFilterField,
    MultipleSelectFilterWidget,
    FormUtils)
from account.models import UserProfile
from resource_inventory.models import Image, Installer, Scenario
from workflow.forms import SearchableSelectMultipleField
from booking.lib import get_user_items, get_user_field_opts


class QuickBookingForm(forms.Form):
    purpose = forms.CharField(max_length=1000)
    project = forms.CharField(max_length=400)
    hostname = forms.CharField(max_length=400)

    installer = forms.ModelChoiceField(queryset=Installer.objects.all(), required=False)
    scenario = forms.ModelChoiceField(queryset=Scenario.objects.all(), required=False)

    def __init__(self, data=None, user=None, *args, **kwargs):
        if "default_user" in kwargs:
            default_user = kwargs.pop("default_user")
        else:
            default_user = "you"
        self.default_user = default_user

        super(QuickBookingForm, self).__init__(data=data, **kwargs)

        self.fields["image"] = forms.ModelChoiceField(
            Image.objects.filter(public=True) | Image.objects.filter(owner=user)
        )

        self.fields['users'] = SearchableSelectMultipleField(
            queryset=UserProfile.objects.select_related('user').exclude(user=user),
            items=get_user_items(exclude=user),
            required=False,
            **get_user_field_opts()
        )

        attrs = FormUtils.getLabData(0)
        self.fields['filter_field'] = MultipleSelectFilterField(widget=MultipleSelectFilterWidget(**attrs))
        self.fields['length'] = forms.IntegerField(
            widget=NumberInput(
                attrs={
                    "type": "range",
                    'min': "1",
                    "max": "21",
                    "value": "1"
                }
            )
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


class HostReImageForm(forms.Form):

    image_id = forms.IntegerField()
    host_id = forms.IntegerField()
