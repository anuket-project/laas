##############################################################################
# Copyright (c) 2018 Trevor Bramwell and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
FROM python:3.12
ENV PYTHONUNBUFFERED 1

ADD requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

ADD worker/init.sh /init.sh
ADD src/ /laas_dashboard/

RUN useradd -ms /bin/bash celery
USER celery

WORKDIR /laas_dashboard/
CMD ["/init.sh"]
