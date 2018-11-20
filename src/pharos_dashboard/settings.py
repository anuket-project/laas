##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
import os
from datetime import timedelta

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: don't run with debug turned on in production!
# NOTE: os.environ only returns strings, so making a comparison to
# 'True' here will convert it to the correct Boolean value.
DEBUG = os.environ['DEBUG'] == 'True'
TESTING = os.environ['TEST'] == 'True'

# Application definition

INSTALLED_APPS = [
    'dashboard',
    'resource_inventory',
    'booking',
    'account',
    'notifier',
    'workflow',
    'api',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'bootstrap3',
    'crispy_forms',
    'rest_framework',
    'rest_framework.authtoken',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'account.middleware.TimezoneMiddleware',
]

ROOT_URLCONF = 'pharos_dashboard.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'dashboard.context_processors.debug',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

TEMPLATE_CONTEXT_PROCESSORS = [
    'dashboard.context_processors.debug',
]

WSGI_APPLICATION = 'pharos_dashboard.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/
MEDIA_URL = '/media/'
STATIC_URL = '/static/'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

LOGIN_REDIRECT_URL = '/'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']

BOOTSTRAP3 = {
    'set_placeholder': False,
}

ALLOWED_HOSTS = ['*']

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASS'],
        'HOST': os.environ['DB_SERVICE'],
        'PORT': os.environ['DB_PORT']
    }
}

# Rest API Settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.FilterSet',),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    )
}

MEDIA_ROOT = '/media'
STATIC_ROOT = '/static'

# Jira Settings
CREATE_JIRA_TICKET = False

JIRA_URL = os.environ['JIRA_URL']

JIRA_USER_NAME = os.environ['JIRA_USER_NAME']
JIRA_USER_PASSWORD = os.environ['JIRA_USER_PASSWORD']

OAUTH_CONSUMER_KEY = os.environ['OAUTH_CONSUMER_KEY']
OAUTH_CONSUMER_SECRET = os.environ['OAUTH_CONSUMER_SECRET']

OAUTH_REQUEST_TOKEN_URL = JIRA_URL + '/plugins/servlet/oauth/request-token'
OAUTH_ACCESS_TOKEN_URL = JIRA_URL + '/plugins/servlet/oauth/access-token'
OAUTH_AUTHORIZE_URL = JIRA_URL + '/plugins/servlet/oauth/authorize'

OAUTH_CALLBACK_URL = os.environ['DASHBOARD_URL'] + '/accounts/authenticated'

# Celery Settings
CELERY_TIMEZONE = 'UTC'

RABBITMQ_URL = 'rabbitmq'
RABBITMQ_DEFAULT_USER = os.environ['RABBITMQ_DEFAULT_USER']
RABBITMQ_DEFAULT_PASS = os.environ['RABBITMQ_DEFAULT_PASS']

BROKER_URL = 'amqp://' + RABBITMQ_DEFAULT_USER + ':' + RABBITMQ_DEFAULT_PASS + '@rabbitmq:5672//'

CELERYBEAT_SCHEDULE = {
    'booking_poll': {
        'task': 'dashboard.tasks.booking_poll',
        'schedule': timedelta(minutes=1)
    },
    'free_hosts': {
        'task': 'dashboard.tasks.free_hosts',
        'schedule': timedelta(minutes=1)
    },
}

# Notifier Settings
EMAIL_HOST = os.environ['EMAIL_HOST']
EMAIL_PORT = os.environ['EMAIL_PORT']
EMAIL_HOST_USER = os.environ['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = os.environ['EMAIL_HOST_PASSWORD']
EMAIL_USE_TLS = True
DEFAULT_EMAIL_FROM = os.environ.get('DEFAULT_EMAIL_FROM', 'webmaster@localhost')
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
