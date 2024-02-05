##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


import django.forms as forms
import pytz as pytz
from django.utils.translation import gettext_lazy as _

from account.models import UserProfile


class AccountPreferencesForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['timezone', 'public_user']
        labels = {
        }
    timezone = forms.ChoiceField(widget=forms.Select(attrs={'style': 'width: 200px;', 'class': 'form-control'}) ,choices=[(x, x) for x in pytz.common_timezones], initial='UTC')
    public_user = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={}))