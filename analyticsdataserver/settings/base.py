"""Common settings and globals."""

from os import environ
from os.path import abspath, basename, dirname, join, normpath
from sys import stderr


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
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
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


########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = normpath(join(SITE_ROOT, 'media'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'
########## END MEDIA CONFIGURATION


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
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'analytics_data_api.v0.middleware.LearnerEngagementTimelineNotFoundErrorMiddleware',
    'analytics_data_api.v0.middleware.LearnerNotFoundErrorMiddleware',
    'analytics_data_api.v0.middleware.CourseNotSpecifiedErrorMiddleware',
    'analytics_data_api.v0.middleware.CourseKeyMalformedErrorMiddleware',
    'analytics_data_api.v0.middleware.ParameterValueErrorMiddleware',
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
)

LOCAL_APPS = (
    'analytics_data_api',
    'analytics_data_api.v0',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
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
        }
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
        'rest_framework_csv.renderers.CSVRenderer',
    )
}
########## END REST FRAMEWORK CONFIGURATION


########## ANALYTICS DATA API CONFIGURATION

ANALYTICS_DATABASE = 'default'
DATABASE_ROUTERS = ['analyticsdataserver.router.AnalyticsApiRouter']

ENABLE_ADMIN_SITE = False

# base url to generate link to user api
LMS_USER_ACCOUNT_BASE_URL = None

########## END ANALYTICS DATA API CONFIGURATION


DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%dT%H%M%S'
