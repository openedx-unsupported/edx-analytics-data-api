"""Common settings and globals."""

from __future__ import absolute_import

from os import environ
from os.path import abspath, basename, dirname, join, normpath
from sys import stderr

from enterprise_data_roles.constants import (
    ENTERPRISE_DATA_ADMIN_ROLE,
    SYSTEM_ENTERPRISE_ADMIN_ROLE,
    SYSTEM_ENTERPRISE_OPERATOR_ROLE
)

########## PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)

# Site name:
SITE_NAME = basename(DJANGO_ROOT)
########## END PATH CONFIGURATION


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False
########## END DEBUG CONFIGURATION


########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('Your Name', 'your_email@example.com'),
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
########## END MANAGER CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DEFAULT_MYSQL_OPTIONS = {
    'connect_timeout': 10,
    'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
}
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': 'localhost',
        'NAME': 'analytics-api',
        'OPTIONS': DEFAULT_MYSQL_OPTIONS,
        'PASSWORD': 'password',
        'PORT': '3306',
        'USER': 'api001',
        'ATOMIC_REQUESTS': False,
    },
    'reports': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': 'localhost',
        'NAME': 'reports',
        'OPTIONS': DEFAULT_MYSQL_OPTIONS,
        'PASSWORD': 'password',
        'PORT': '3306',
        'USER': 'reports001',
    }
}
########## END DATABASE CONFIGURATION

########## ELASTICSEARCH CONFIGURATION
ELASTICSEARCH_LEARNERS_HOST = environ.get('ELASTICSEARCH_LEARNERS_HOST', None)
ELASTICSEARCH_LEARNERS_INDEX = environ.get('ELASTICSEARCH_LEARNERS_INDEX', None)
ELASTICSEARCH_LEARNERS_UPDATE_INDEX = environ.get('ELASTICSEARCH_LEARNERS_UPDATE_INDEX', None)

# access credentials for signing requests to AWS.
# For more information see http://docs.aws.amazon.com/general/latest/gr/signing_aws_api_requests.html
ELASTICSEARCH_AWS_ACCESS_KEY_ID = None
ELASTICSEARCH_AWS_SECRET_ACCESS_KEY = None
# override the default elasticsearch connection class and useful for signing certificates
# e.g. 'analytics_data_api.v0.connections.BotoHttpConnection'
ELASTICSEARCH_CONNECTION_CLASS = None
# only needed with BotoHttpConnection, e.g. 'us-east-1'
ELASTICSEARCH_CONNECTION_DEFAULT_REGION = None
########## END ELASTICSEARCH CONFIGURATION

########## GENERAL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#time-zone
TIME_ZONE = 'UTC'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = False

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = False

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
########## END GENERAL CONFIGURATION


########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = normpath(join(SITE_ROOT, 'assets'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'static')),
)

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
########## END STATIC FILE CONFIGURATION


########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key should only be used for development and testing.
SECRET_KEY = r"g)rke*$-ox1yursa_l!rjnh6tn!pd+qs^8i03xb0!#50#zhb%k"
########## END SECRET CONFIGURATION


########## SITE CONFIGURATION
# Hosts/domain names that are valid for this site
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []
########## END SITE CONFIGURATION


########## FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    normpath(join(SITE_ROOT, 'fixtures')),
)
########## END FIXTURE CONFIGURATION


########## TEMPLATE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            normpath(join(SITE_ROOT, 'templates')),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
            ],
        },
    }
]
########## END TEMPLATE CONFIGURATION


########## MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE_CLASSES = (
    # Default Django middleware.
    'edx_django_utils.cache.middleware.RequestCacheMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'crum.CurrentRequestUserMiddleware',
    'django.middleware.common.CommonMiddleware',
    'edx_rest_framework_extensions.auth.jwt.middleware.JwtAuthCookieMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'edx_django_utils.cache.middleware.TieredCacheMiddleware',
    'edx_rest_framework_extensions.middleware.RequestMetricsMiddleware',
    'edx_rest_framework_extensions.auth.jwt.middleware.EnsureJWTAuthSettingsMiddleware',
    'waffle.middleware.WaffleMiddleware',
    'analytics_data_api.v0.middleware.LearnerEngagementTimelineNotFoundErrorMiddleware',
    'analytics_data_api.v0.middleware.LearnerNotFoundErrorMiddleware',
    'analytics_data_api.v0.middleware.CourseNotSpecifiedErrorMiddleware',
    'analytics_data_api.v0.middleware.CourseKeyMalformedErrorMiddleware',
    'analytics_data_api.v0.middleware.ParameterValueErrorMiddleware',
    'analytics_data_api.v0.middleware.ReportFileNotFoundErrorMiddleware',
    'analytics_data_api.v0.middleware.CannotCreateDownloadLinkErrorMiddleware',
)
########## END MIDDLEWARE CONFIGURATION


########## URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = '%s.urls' % SITE_NAME
########## END URL CONFIGURATION


########## APP CONFIGURATION
DJANGO_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
)

THIRD_PARTY_APPS = (
    'release_util',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_swagger',
    'django_countries',
    'storages',
    'enterprise_data',
    'rules.apps.AutodiscoverRulesConfig',
    'corsheaders',
    'waffle',
)

LOCAL_APPS = (
    'analytics_data_api',
    'analytics_data_api.v0',
    'enterprise_data_roles',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTHENTICATION_BACKENDS = [
    'rules.permissions.ObjectPermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
]
########## END APP CONFIGURATION


########## LOGGING CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging
# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'stream': stderr,
        },
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'analyticsdata': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        },
        'enterprise_data': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True
        },
        'rules': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        # See https://elasticutils.readthedocs.io/en/latest/debugging.html
        # INFO-level logs tell us when nodes fail and are resurrected.
        'elasticsearch': {
            'handlers': ['console'],
            'level': 'WARNING'
        },
        # elasticsearch.trace logs are fired for every single request
        # with an INFO or DEBUG level.  They're noisy and not terribly
        # userful for debugging, so we'll just propagate them to the
        # 'elasticsearch' log bucket which only accepts 'WARNING'
        # level logs.
        'elasticsearch.trace': {
            'handlers': ['null'],
            'propagate': False
        },
    },
}
########## END LOGGING CONFIGURATION


########## WSGI CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = '%s.wsgi.application' % SITE_NAME
########## END WSGI CONFIGURATION


########## REST FRAMEWORK CONFIGURATION
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ],

    'DEFAULT_AUTHENTICATION_CLASSES': (
        # Most clients will use token authentication
        'rest_framework.authentication.TokenAuthentication',

        # For the browseable API
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        'analytics_data_api.renderers.PaginatedCsvRenderer',
    )
}
########## END REST FRAMEWORK CONFIGURATION


########## ANALYTICS DATA API CONFIGURATION

ANALYTICS_DATABASE = 'default'
DATABASE_ROUTERS = ['analyticsdataserver.router.AnalyticsApiRouter']

LMS_BASE_URL = None

# base url to generate link to user api
LMS_USER_ACCOUNT_BASE_URL = None

# settings for report downloads
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_ROOT = normpath(join(SITE_ROOT, 'static', 'reports'))
MEDIA_URL = 'http://localhost:8100/static/reports/'
COURSE_REPORT_FILE_LOCATION_TEMPLATE = '{course_id}_{report_name}.csv'
ENABLED_REPORT_IDENTIFIERS = ('problem_response',)
REPORT_DOWNLOAD_BACKEND = {
    DEFAULT_FILE_STORAGE: 'django.core.files.storage.FileSystemStorage',
    MEDIA_ROOT: MEDIA_ROOT,
    MEDIA_URL: MEDIA_URL,
    COURSE_REPORT_FILE_LOCATION_TEMPLATE: ENABLED_REPORT_IDENTIFIERS
}
# Warning: using 0 or None for these can alter the structure of the REST response.
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
AGGREGATE_PAGE_SIZE = 10

# Maximum number of GET/POST parameters that will be read before a
# SuspiciousOperation (TooManyFieldsSent) is raised.
# None indicates no maximum.
# We need to set this to None so that we can pass in a large number of Course IDs
# to course_summaries/
DATA_UPLOAD_MAX_NUMBER_FIELDS = None

JWT_AUTH = {
    'JWT_ALGORITHM': 'HS256',
    'JWT_AUDIENCE': 'lms-key',
    'JWT_AUTH_COOKIE': 'edx-jwt-cookie',
    'JWT_ISSUER': [
        {
            'AUDIENCE': 'SET-ME-PLEASE',
            'ISSUER': 'http://127.0.0.1:8000/oauth2',
            'SECRET_KEY': 'SET-ME-PLEASE'
        }
    ],
    'JWT_DECODE_HANDLER': 'edx_rest_framework_extensions.auth.jwt.decoder.jwt_decode_handler',
    'JWT_VERIFY_AUDIENCE': False,
    'JWT_AUTH_COOKIE': 'edx-jwt-cookie',
    'JWT_PUBLIC_SIGNING_JWK_SET': None,
    'JWT_AUTH_COOKIE_HEADER_PAYLOAD': 'edx-jwt-cookie-header-payload',
    'JWT_AUTH_COOKIE_SIGNATURE': 'edx-jwt-cookie-signature',
}

########## END ANALYTICS DATA API CONFIGURATION


DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%dT%H%M%S'

########## EDX ENTERPRISE DATA CONFIGURATION

SYSTEM_TO_FEATURE_ROLE_MAPPING = {
    SYSTEM_ENTERPRISE_ADMIN_ROLE: [ENTERPRISE_DATA_ADMIN_ROLE],
    SYSTEM_ENTERPRISE_OPERATOR_ROLE: [ENTERPRISE_DATA_ADMIN_ROLE],
}

########## EDX ENTERPRISE DATA CONFIGURATION
API_AUTH_TOKEN = 'put-your-api-token-here'
CSRF_COOKIE_SECURE = False

EXTRA_APPS = []
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
SOCIAL_AUTH_EDX_OAUTH2_KEY = "analytics_api-sso-key"
SOCIAL_AUTH_EDX_OAUTH2_SECRET = "-sso-secret"
SOCIAL_AUTH_EDX_OAUTH2_ISSUER = "http://127.0.0.1:8000"
SOCIAL_AUTH_EDX_OAUTH2_URL_ROOT = "http://127.0.0.1:8000"
SOCIAL_AUTH_EDX_OAUTH2_LOGOUT_URL = "http://127.0.0.1:8000/logout"

BACKEND_SERVICE_EDX_OAUTH2_KEY = "analytics_api-backend-service-key"
BACKEND_SERVICE_EDX_OAUTH2_SECRET = "analytics_api-backend-service-secret"
BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL = "http://127.0.0.1:8000/oauth2"
EDX_DRF_EXTENSIONS = {
    "OAUTH2_USER_INFO_URL": "http://127.0.0.1:8000/oauth2/user_info"
}
API_ROOT = None
MEDIA_STORAGE_BACKEND = {
    'DEFAULT_FILE_STORAGE': 'django.core.files.storage.FileSystemStorage',
    'MEDIA_ROOT': MEDIA_ROOT,
    'MEDIA_URL': MEDIA_URL
}
# Set these to the correct values for your OAuth2/OpenID Connect provider (e.g., devstack)
SOCIAL_AUTH_EDX_OIDC_KEY = 'analytics_api-key'
SOCIAL_AUTH_EDX_OIDC_SECRET = 'analytics_api-secret'
SOCIAL_AUTH_EDX_OIDC_URL_ROOT = 'http://127.0.0.1:8000/oauth2'
SOCIAL_AUTH_EDX_OIDC_LOGOUT_URL = 'http://127.0.0.1:8000/logout'
SOCIAL_AUTH_EDX_OIDC_ID_TOKEN_DECRYPTION_KEY = 'analytics_api-secret'
SOCIAL_AUTH_REDIRECT_IS_HTTPS = False
SOCIAL_AUTH_EDX_OIDC_PUBLIC_URL_ROOT = 'http://127.0.0.1:8000/oauth2'
SOCIAL_AUTH_EDX_OIDC_ISSUER = 'http://127.0.0.1:8000/oauth2'
