##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Sawyer Bergeron, Parker Berberian, and others
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
from django.conf.urls import url
from django.urls import path

from api.views import (
    lab_profile,
    lab_status,
    lab_inventory,
    lab_downtime,
    specific_job,
    specific_task,
    new_jobs,
    current_jobs,
    done_jobs,
    update_host_bmc,
    lab_host,
    get_pdf,
    get_idf,
    lab_users,
    lab_user,
    GenerateTokenView,
    analytics_job,
    user_bookings,
    specific_booking,
    extend_booking,
    make_booking,
    list_labs,
    all_users,
    images_for_template,
    available_templates,
    resource_ci_metadata,
    resource_ci_userdata,
    resource_ci_userdata_directory,
    all_images,
    all_opsyss,
    single_image,
    single_opsys,
    create_ci_file,
)

urlpatterns = [
    path('labs/<slug:lab_name>/opsys/<slug:opsys_id>', single_opsys),
    path('labs/<slug:lab_name>/image/<slug:image_id>', single_image),
    path('labs/<slug:lab_name>/opsys', all_opsyss),
    path('labs/<slug:lab_name>/image', all_images),
    path('labs/<slug:lab_name>/profile', lab_profile),
    path('labs/<slug:lab_name>/status', lab_status),
    path('labs/<slug:lab_name>/inventory', lab_inventory),
    path('labs/<slug:lab_name>/downtime', lab_downtime),
    path('labs/<slug:lab_name>/hosts/<slug:host_id>', lab_host),
    path('labs/<slug:lab_name>/hosts/<slug:host_id>/bmc', update_host_bmc),
    path('labs/<slug:lab_name>/booking/<int:booking_id>/pdf', get_pdf, name="get-pdf"),
    path('labs/<slug:lab_name>/booking/<int:booking_id>/idf', get_idf, name="get-idf"),
    path('labs/<slug:lab_name>/jobs/<int:job_id>', specific_job),
    path('labs/<slug:lab_name>/jobs/<int:job_id>/<slug:task_id>', specific_task),
    path('labs/<slug:lab_name>/jobs/<int:job_id>/cidata/<slug:resource_id>/user-data', resource_ci_userdata_directory, name="specific-user-data"),
    path('labs/<slug:lab_name>/jobs/<int:job_id>/cidata/<slug:resource_id>/meta-data', resource_ci_metadata, name="specific-meta-data"),
    path('labs/<slug:lab_name>/jobs/<int:job_id>/cidata/<slug:resource_id>/<int:file_id>/user-data', resource_ci_userdata, name="user-data-dir"),
    path('labs/<slug:lab_name>/jobs/new', new_jobs),
    path('labs/<slug:lab_name>/jobs/current', current_jobs),
    path('labs/<slug:lab_name>/jobs/done', done_jobs),
    path('labs/<slug:lab_name>/jobs/getByType/DATA', analytics_job),
    path('labs/<slug:lab_name>/users', lab_users),
    path('labs/<slug:lab_name>/users/<int:user_id>', lab_user),

    path('booking', user_bookings),
    path('booking/<int:booking_id>', specific_booking),
    path('booking/<int:booking_id>/extendBooking/<int:days>', extend_booking),
    path('booking/makeBooking', make_booking),

    path('resource_inventory/availableTemplates', available_templates),
    path('resource_inventory/<int:template_id>/images', images_for_template),

    path('resource_inventory/cloud/create', create_ci_file),

    path('users', all_users),
    path('labs', list_labs),

    url(r'^token$', GenerateTokenView.as_view(), name='generate_token'),
]
