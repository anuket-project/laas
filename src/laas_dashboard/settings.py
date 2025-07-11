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
DEBUG = os.environ.get('DEBUG') == 'True'
TESTING = os.environ.get('TEST') == 'True'

# Application definition

INSTALLED_APPS = [
    'booking_api',
    'dashboard',
    'resource_inventory',
    'booking',
    'account',
    'notifier',
    'workflow',
    'api',
    'analytics',
    'liblaas',
    'django.contrib.admin',
    'django.contrib.auth',
    'mozilla_django_oidc',  # needs to be defined after auth
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    "whitenoise.runserver_nostatic",
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'bootstrap4',
    'rest_framework',
    'rest_framework.authtoken',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "account.middleware.ActiveUserMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "account.middleware.TimezoneMiddleware"
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend', 'account.views.MyOIDCAB']
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.AllowAllUsersModelBackend']

AUTH_SETTING = os.environ.get('AUTH_SETTING')

if AUTH_SETTING == 'LFID':
    # OpenID Authentications
    AUTHENTICATION_BACKENDS.append('account.views.MyOIDCAB')
    OIDC_RP_CLIENT_ID = os.environ.get('OIDC_CLIENT_ID')
    OIDC_RP_CLIENT_SECRET = os.environ.get('OIDC_CLIENT_SECRET')

    OIDC_OP_AUTHORIZATION_ENDPOINT = os.environ.get('OIDC_AUTHORIZATION_ENDPOINT')
    OIDC_OP_TOKEN_ENDPOINT = os.environ.get('OIDC_TOKEN_ENDPOINT')
    OIDC_OP_USER_ENDPOINT = os.environ.get('OIDC_USER_ENDPOINT')

    LOGIN_REDIRECT_URL = os.environ.get('DASHBOARD_URL')
    LOGOUT_REDIRECT_URL = os.environ.get('DASHBOARD_URL')

    OIDC_RP_SIGN_ALGO = os.environ.get("OIDC_RP_SIGN_ALGO")

    if OIDC_RP_SIGN_ALGO == "RS256":
        OIDC_OP_JWKS_ENDPOINT = os.environ.get("OIDC_OP_JWKS_ENDPOINT")
elif AUTH_SETTING == 'DEV_NORMAL':
    
    print("dev mode")
else:
    raise Exception('AUTH_SETTING set to invalid value')

# This is for LFID auth setups w/ an HTTPS proxy
if os.environ.get('EXPECT_HOST_FORWARDING') == 'True':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', "https")
    USE_X_FORWARDED_HOST = True

ROOT_URLCONF = 'laas_dashboard.urls'

PROJECT = os.environ.get("PROJECT", "")  # the project for the current deployment (i.e. anuket or lfedge)
HOST_DOMAIN = os.environ.get("HOST_DOMAIN", "") # Domain for provisioned hosts (i.e opnfv.iol.unh.edu or akr.iol.unh.edu)
LIBLAAS_BASE_URL = os.environ.get("LIBLAAS_BASE_URL") # API URL
TEMPLATE_DIRS = ["base"]  # where all the base templates are
SUB_PROJECTS = os.environ.get("SUB_PROJECTS", "").split(',')

# If the user has a custom template directory,
# We should search that first. Then we search the
# root template directory so that we can extend the base
# templates within the custom template dir.
if PROJECT:
    TEMPLATE_DIRS = [PROJECT, ""] + TEMPLATE_DIRS

# all template dirs are relative to /project_root/templates/
dirs = [os.path.join(BASE_DIR, "templates", d) for d in TEMPLATE_DIRS]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': dirs,
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

WSGI_APPLICATION = 'laas_dashboard.wsgi.application'

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


USE_TZ = True

MEDIA_URL = "/media/"
MEDIA_ROOT = "/media"

STATIC_HOST = os.environ.get("DJANGO_STATIC_HOST", "")

STATIC_URL = STATIC_HOST + "/collected_static/"

STATIC_ROOT = os.environ.get("STATIC_ROOT", os.path.join(BASE_DIR, "collected_static"))


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

LOGIN_REDIRECT_URL = '/'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

BOOTSTRAP3 = {
    'set_placeholder': False,
}

ALLOWED_HOSTS = ['*']

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASS'),
        'HOST': os.environ.get('DB_SERVICE'),
        'PORT': os.environ.get('DB_PORT')
    }
}

DEFAULT_AUTO_FIELD='django.db.models.AutoField' 

# Rest API Settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.FilterSet',),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        ]
}


OAUTH_CONSUMER_KEY = os.environ.get('OAUTH_CONSUMER_KEY')
OAUTH_CONSUMER_SECRET = os.environ.get('OAUTH_CONSUMER_SECRET')

OAUTH_CALLBACK_URL = os.environ.get('DASHBOARD_URL') + '/accounts/authenticated'

# Celery Settings
CELERY_TIMEZONE = 'UTC'

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_PORT = os.environ.get('RABBITMQ_PORT', '5672')
RABBITMQ_DEFAULT_USER = os.environ.get('RABBITMQ_DEFAULT_USER')
RABBITMQ_DEFAULT_PASS = os.environ.get('RABBITMQ_DEFAULT_PASS')

CELERY_BROKER_URL = f"amqp://{RABBITMQ_DEFAULT_USER}:{RABBITMQ_DEFAULT_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"

CELERY_BEAT_SCHEDULE = {
    'booking_poll': {
        'task': 'dashboard.tasks.end_expired_bookings',
        'schedule': timedelta(minutes=1)
    },
    'notification_poll': {
        'task': 'dashboard.tasks.send_notifications',
        'schedule': timedelta(minutes=2)
    }
}

# Notifier Settings
EXPIRE_LIFETIME = 12  # Minimum lifetime of booking to send notification
EXPIRE_HOURS = 48  # Notify when booking is expiring within this many hours

SITE_CONTACT = os.environ.get("SITE_CONTACT")
EVE_DOCS_URL = os.environ.get("EVE_DOCS_URL", "")