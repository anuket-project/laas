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


class AccountSettingsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['company', 'email_addr', 'ssh_public_key', 'pgp_public_key', 'timezone']
        labels = {
            'email_addr': _('Email Address'),
            'ssh_public_key': _('SSH Public Key'),
            'pgp_public_key': _('PGP Public Key')
        }

    timezone = forms.ChoiceField(choices=[(x, x) for x in pytz.common_timezones], initial='UTC')
