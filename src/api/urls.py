##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


"""pharos_dashboard URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.urls import path
from rest_framework import routers

from api.views import *

router = routers.DefaultRouter()
router.register(r'bookings', BookingViewSet)
router.register(r'user', UserViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    path('labs/<slug:lab_name>/profile', lab_profile),
    path('labs/<slug:lab_name>/status', lab_status),
    path('labs/<slug:lab_name>/inventory', lab_inventory),
    path('labs/<slug:lab_name>/jobs/<int:job_id>', specific_job),
    path('labs/<slug:lab_name>/jobs/<int:job_id>/<slug:task_id>', specific_task),
    path('labs/<slug:lab_name>/jobs/new', new_jobs),
    path('labs/<slug:lab_name>/jobs/current', current_jobs),
    path('labs/<slug:lab_name>/jobs/done', done_jobs),
    url(r'^token$', GenerateTokenView.as_view(), name='generate_token'),
]
