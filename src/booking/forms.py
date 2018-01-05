##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


import django.forms as forms

from booking.models import Installer, Scenario, Opsys
from datetime import datetime

class BookingForm(forms.Form):
    fields = ['start', 'end', 'purpose', 'opsys', 'reset', 'installer', 'scenario']

    start = forms.DateTimeField()
    end = forms.DateTimeField()
    reset = forms.ChoiceField(choices = ((True, 'Yes'),(False, 'No')), label="Reset System", initial='False', required=False)
    purpose = forms.CharField(max_length=300)
    opsys = forms.ModelChoiceField(queryset=Opsys.objects.all(), required=False)
    installer = forms.ModelChoiceField(queryset=Installer.objects.all(), required=False)
    scenario = forms.ModelChoiceField(queryset=Scenario.objects.all(), required=False)

class BookingEditForm(forms.Form):
    fields = ['start', 'end', 'purpose', 'opsys', 'reset', 'installer', 'scenario']

    start = forms.DateTimeField()
    end = forms.DateTimeField()
    purpose = forms.CharField(max_length=300)
    opsys = forms.ModelChoiceField(queryset=Opsys.objects.all(), required=False)
    installer = forms.ModelChoiceField(queryset=Installer.objects.all(), required=False)
    scenario = forms.ModelChoiceField(queryset=Scenario.objects.all(), required=False)
    reset = forms.ChoiceField(choices = ((True, 'Yes'),(False, 'No')), label="Reset System", initial='False', required=True)


    def __init__(self, *args, **kwargs ):
        cloned_kwargs = {}
        cloned_kwargs['purpose'] = kwargs.pop('purpose')
        cloned_kwargs['start'] = kwargs.pop('start')
        cloned_kwargs['end'] = kwargs.pop('end')
        if 'installer' in kwargs:
            cloned_kwargs['installer'] = kwargs.pop('installer')
        if 'scenario' in kwargs:
            cloned_kwargs['scenario'] = kwargs.pop('scenario')
        super(BookingEditForm, self).__init__( *args, **kwargs)

        self.fields['purpose'].initial = cloned_kwargs['purpose']
        self.fields['start'].initial = cloned_kwargs['start'].strftime('%m/%d/%Y %H:%M')
        self.fields['end'].initial = cloned_kwargs['end'].strftime('%m/%d/%Y %H:%M')
        try:
            self.fields['installer'].initial = cloned_kwargs['installer'].id
        except KeyError:
            pass
        except AttributeError:
            pass
        try:
            self.fields['scenario'].initial = cloned_kwargs['scenario'].id
        except KeyError:
            pass
        except AttributeError:
            pass
