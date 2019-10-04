##############################################################################
# Copyright (c) 2018 Trevor Bramwell and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
FROM node as static
RUN npm install -g bower
ADD src/static/ /static
WORKDIR /static/
RUN bower install --allow-root

FROM python:3.5
ENV PYTHONUNBUFFERED 1

ADD requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

ADD web/init.sh /init.sh
ADD src/ /laas_dashboard/
COPY --from=static /static/ laas_dashboard/static/

WORKDIR /laas_dashboard/
CMD ["/init.sh"]
