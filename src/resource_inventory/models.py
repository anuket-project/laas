##############################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
# Copyright (c) 2020 Sawyer Bergeron, Sean Smith, others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
############################################################################################################################################################
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
# Copyright (c) 2020 Sawyer Bergeron, Sean Smith, others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.contrib.auth.models import User

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
import traceback
import json

import re
from collections import Counter

from account.models import Lab
from dashboard.utils import AbstractModelQuery

# Keep for now until migrations are made, otherwise django will get angry
def get_default_remote_info():
    pass

def get_sentinal_opnfv_role():
    pass
