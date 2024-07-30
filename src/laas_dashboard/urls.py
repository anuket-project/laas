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
from django.conf import settings
from django.urls import include, path, re_path
from django.conf.urls.static import static
from django.contrib import admin


urlpatterns = [

    path('workflow/', include('workflow.urls', namespace='workflow')),
    path('', include('dashboard.urls', namespace='dashboard')),
    path('booking/', include('booking.urls', namespace='booking')),
    path('accounts/', include('account.urls', namespace='account')),
    re_path(r'^admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/', include('api.urls')),
    path('oidc/', include('mozilla_django_oidc.urls')),
    path('resource/', include('resource_inventory.urls', namespace='resource')),
    path('liblaas/', include('liblaas.urls', namespace='liblaas'))
]

handler404 = 'dashboard.views.handler404'
handler500 = 'dashboard.views.handler500'

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
