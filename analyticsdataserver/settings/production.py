"""Production settings and globals."""


from os import environ
from base import *
import yaml
from analyticsdataserver.logsettings import get_logger_config

# Normally you should not import ANYTHING from Django directly
# into your settings, but ImproperlyConfigured is an exception.
from django.core.exceptions import ImproperlyConfigured


LOGGING = get_logger_config()

def get_env_setting(setting):
    """Get the environment setting or return exception."""
    try:
        return environ[setting]
    except KeyError:
        error_msg = "Set the %s env variable" % setting
        raise ImproperlyConfigured(error_msg)

########## HOST CONFIGURATION
# See: https://docs.djangoproject.com/en/1.5/releases/1.5/#allowed-hosts-required-in-production
ALLOWED_HOSTS = ['*']
########## END HOST CONFIGURATION

CONFIG_FILE=get_env_setting('ANALYTICS_API_CFG')

with open(CONFIG_FILE) as f:
  config_from_yaml = yaml.load(f)

vars().update(config_from_yaml)

DB_OVERRIDES = dict(
    PASSWORD=os.environ.get('DB_MIGRATION_PASS', DATABASES['default']['PASS']),
    ENGINE=os.environ.get('DB_MIGRATION_ENGINE', DATABASES['default']['ENGINE']),
    USER=os.environ.get('DB_MIGRATION_USER', DATABASES['default']['USER']),
    NAME=os.environ.get('DB_MIGRATION_NAME', DATABASES['default']['NAME']),
    HOST=os.environ.get('DB_MIGRATION_HOST', DATABASES['default']['HOST']),
    PORT=os.environ.get('DB_MIGRATION_PORT', DATABASES['default']['PORT']),
)

for override, value in DB_OVERRIDES.iteritems():
    DATABASES['default'][override] = value
