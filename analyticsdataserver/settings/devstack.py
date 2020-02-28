"""Devstack settings."""

from analyticsdataserver.settings.local import *

ALLOWED_HOSTS += ['edx.devstack.analyticsapi']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'analytics-api',
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

ELASTICSEARCH_LEARNERS_HOST = "edx.devstack.elasticsearch"
LMS_BASE_URL = "http://edx.devstack.lms:18000/"
