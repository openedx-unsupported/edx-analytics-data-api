"""Test settings and globals."""
import os

from analyticsdataserver.settings.base import *

########## IN-MEMORY TEST DATABASE
DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("DB_NAME", ":memory:"),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASS", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", ""),
    },
    'analytics': {
        'ENGINE': os.environ.get("DB_ENGINE", "django.db.backends.sqlite3"),
        'NAME': os.environ.get("DB_NAME", normpath(join(DJANGO_ROOT, 'analytics.db'))),
        'USER': os.environ.get("DB_USER", ""),
        'PASSWORD': os.environ.get("DB_PASS", ""),
        'HOST': os.environ.get("DB_HOST", ""),
        'PORT': os.environ.get("DB_PORT", ""),
    },
    'analytics_v1': {
        'ENGINE': os.environ.get("DB_ENGINE", "django.db.backends.sqlite3"),
        'NAME': os.environ.get("DB_NAME", normpath(join(DJANGO_ROOT, 'analytics_v1.db'))),
        'USER': os.environ.get("DB_USER", ""),
        'PASSWORD': os.environ.get("DB_PASS", ""),
        'HOST': os.environ.get("DB_HOST", ""),
        'PORT': os.environ.get("DB_PORT", ""),
    },
}

ANALYTICS_DATABASE = 'analytics'
ANALYTICS_DATABASE_V1 = 'analytics_v1'
ENTERPRISE_REPORTING_DB_ALIAS = 'default'

# Silence elasticsearch during tests
LOGGING['loggers']['elasticsearch']['handlers'] = ['null']

LMS_BASE_URL = 'http://lms-host'

LMS_USER_ACCOUNT_BASE_URL = 'http://lms-host'

# Default elasticsearch port when running locally
ELASTICSEARCH_LEARNERS_HOST = environ.get("ELASTICSEARCH_LEARNERS_HOST", 'http://localhost:9223/')
ELASTICSEARCH_LEARNERS_INDEX = 'roster_test_001'
ELASTICSEARCH_LEARNERS_INDEX_ALIAS = 'roster_test'
ELASTICSEARCH_LEARNERS_UPDATE_INDEX = 'index_update_test'

# Default the django-storage settings so we can test easily
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = 'xxxxx'
AWS_SECRET_ACCESS_KEY = 'xxxxx'
AWS_STORAGE_BUCKET_NAME = 'fake-bucket'
AWS_DEFAULT_ACL = None
FTP_STORAGE_LOCATION = 'ftp://localhost:80/path'

# Default settings for report download endpoint
COURSE_REPORT_FILE_LOCATION_TEMPLATE = '/{course_id}_{report_name}.csv'
COURSE_REPORT_DOWNLOAD_EXPIRY_TIME = 120
