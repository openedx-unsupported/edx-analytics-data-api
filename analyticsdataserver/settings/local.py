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

# In Insights, we run this API as a separate service called "analyticsapi" to run acceptance/integration tests. Docker
# saves the service name as a host in the Insights container so it can reach the API by requesting http://analyticsapi/.
# However, in Django 1.10.3, the HTTP_HOST header of requests started to be checked against the ALLOWED_HOSTS setting
# even in DEBUG=True mode. Here, we add the Docker service name "analyticsapi" to the default set of local allowed
# hosts.
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '::1', 'analyticsapi']

########## END ANALYTICS DATA API CONFIGURATION
