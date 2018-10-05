#!/bin/bash -e
##############################################################################
# Copyright (c) 2018 Trevor Bramwell and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
python manage.py migrate && \
python manage.py collectstatic --no-input && \
gunicorn pharos_dashboard.wsgi -b 0.0.0.0:8000
