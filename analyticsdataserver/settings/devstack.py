"""Devstack settings."""

import os

from analyticsdataserver.settings.local import *

########## DATABASE CONFIGURATION
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'analytics-api',
        'USER': 'api001',
        'PASSWORD': 'password',
        'HOST': 'edx.devstack.mysql',
        'PORT': '3306',
    },
    'analytics_v1': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'reports_v1',
        'USER': 'api001',
        'PASSWORD': 'password',
        'HOST': 'edx.devstack.mysql',
        'PORT': '3306',
    },
    'analytics': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'reports',
        'USER': 'reports001',
        'PASSWORD': 'password',
        'HOST': 'edx.devstack.mysql',
        'PORT': '3306',
    }
}

ANALYTICS_DATABASE_V1 = 'analytics_v1'

DB_OVERRIDES = dict(
    USER=os.environ.get('DB_USER', DATABASES['default']['USER']),
    PASSWORD=os.environ.get('DB_PASSWORD', DATABASES['default']['PASSWORD']),
    HOST=os.environ.get('DB_HOST', DATABASES['default']['HOST']),
    PORT=os.environ.get('DB_PORT', DATABASES['default']['PORT']),
)

for override, value in DB_OVERRIDES.items():
    DATABASES['default'][override] = value
    DATABASES['analytics'][override] = value
    DATABASES['analytics_v1'][override] = value

DATABASE_ROUTERS = ['analyticsdataserver.router.AnalyticsAPIRouter', 'analyticsdataserver.router.AnalyticsModelsRouter']

########## END DATABASE CONFIGURATION

ALLOWED_HOSTS += ['edx.devstack.analyticsapi']

LMS_BASE_URL = "http://edx.devstack.lms:18000/"
