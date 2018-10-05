#!/bin/bash -e
##############################################################################
# Copyright (c) 2018 Trevor Bramwell and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
celery -A pharos_dashboard worker -l info -B --schedule=~/celerybeat-schedule
