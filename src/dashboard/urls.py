##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


"""
laas_dashboard URL Configuration.

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
from django.urls import path
from dashboard.views import (
    landing_view,
    lab_list_view,
    host_profile_detail_view
)

app_name = 'dashboard'
urlpatterns = [
    path('', landing_view, name='index'),
    path('lab/', lab_list_view, name='all_labs'),
    path('hosts/', host_profile_detail_view, name="hostprofile_detail")
]
