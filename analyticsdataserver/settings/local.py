"""Development settings and globals."""


from os.path import join, normpath

from analyticsdataserver.settings.base import *


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
########## END DEBUG CONFIGURATION


########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########## END EMAIL CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': normpath(join(DJANGO_ROOT, 'default.db')),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    },
    'analytics': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': normpath(join(DJANGO_ROOT, 'analytics.db')),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}
########## END DATABASE CONFIGURATION


########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
########## END CACHE CONFIGURATION


########## ANALYTICS DATA API CONFIGURATION

ANALYTICS_DATABASE = 'analytics'
ENABLE_ADMIN_SITE = True

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

SWAGGER_SETTINGS = {
    'api_key': 'edx'
}

# These two settings are used in generate_fake_course_data.py.
# Replace with correct values to generate local fake video data.
LMS_BASE_URL = 'http://localhost:8000/'  # the base URL for your running local LMS instance
COURSE_BLOCK_API_AUTH_TOKEN = 'paste auth token here'  # see README for instructions on how to configure this value

########## END ANALYTICS DATA API CONFIGURATION
