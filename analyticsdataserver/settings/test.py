"""Test settings and globals."""

from analyticsdataserver.settings.base import *

########## IN-MEMORY TEST DATABASE
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    },
}

# Silence elasticsearch during tests
LOGGING['loggers']['elasticsearch']['handlers'] = ['null']

INSTALLED_APPS += (
    'django_nose',
)

LMS_USER_ACCOUNT_BASE_URL = 'http://lms-host'

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# Default elasticsearch port when running locally
ELASTICSEARCH_LEARNERS_HOST = 'http://localhost:9223/'
ELASTICSEARCH_LEARNERS_INDEX = 'roster_test'
ELASTICSEARCH_LEARNERS_UPDATE_INDEX = 'index_update_test'
