import unittest.mock as mock
from contextlib import contextmanager

from django.conf import settings
from django.db.utils import ConnectionHandler
from django.test.utils import override_settings

from analytics_data_api.tests.test_utils import set_databases
from analyticsdataserver.tests.utils import TestCaseWithAuthentication


@set_databases
class OperationalEndpointsTest(TestCaseWithAuthentication):
    def test_status(self):
        response = self.client.get('/status', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_authentication_check_failure(self):
        response = self.client.get('/authenticated', follow=True)
        self.assertEqual(response.status_code, 401)

    def test_authentication_check_success(self):
        response = self.authenticated_get('/authenticated', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_health(self):
        self.assert_database_health('OK')

    def assert_database_health(self, status, status_code=200):
        response = self.client.get('/health', follow=True)
        self.assertEqual(
            response.data,
            {
                'overall_status': status,
                'detailed_status': {
                    'database_connection': status
                }
            }
        )
        self.assertEqual(response.status_code, status_code)

    @staticmethod
    @contextmanager
    def override_database_connections(databases):
        with mock.patch('analyticsdataserver.views.connections', ConnectionHandler(databases)):
            yield

    @override_settings(ANALYTICS_DATABASE='reporting')
    def test_read_setting(self):
        databases = dict(settings.DATABASES)
        databases['reporting'] = {}

        with self.override_database_connections(databases):
            self.assert_database_health('UNAVAILABLE', status_code=503)

    # Workaround to remove a setting from django settings. It has to be used in override_settings and then deleted.
    @override_settings(ANALYTICS_DATABASE='reporting')
    def test_default_setting(self):
        del settings.ANALYTICS_DATABASE

        databases = dict(settings.DATABASES)
        databases['reporting'] = {}

        with self.override_database_connections(databases):
            # This would normally return UNAVAILABLE, however we have deleted the settings so it will use the default
            # connection which should be OK.
            self.assert_database_health('OK')
