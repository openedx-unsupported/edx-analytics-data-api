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

    def assert_database_health(
        self,
        overall_status,
        default_db_status='OK',
        analytics_db_status='OK',
        status_code=200
    ):
        response = self.client.get('/health', follow=True)
        self.assertEqual(
            response.data,
            {
                'overall_status': overall_status,
                'detailed_status': {
                    'default_db_status': default_db_status,
                    'analytics_db_status': analytics_db_status,
                }
            }
        )
        self.assertEqual(response.status_code, status_code)

    @staticmethod
    @contextmanager
    def override_database_connections(databases):
        with mock.patch('analyticsdataserver.views.connections', ConnectionHandler(databases)):
            yield

    def test_default_bad_health(self):
        databases = dict(settings.DATABASES)
        databases['default'] = {}
        with self.override_database_connections(databases):
            self.assert_database_health('UNAVAILABLE', default_db_status='UNAVAILABLE', status_code=503)

    @override_settings(ANALYTICS_DATABASE='reporting')
    def test_db_bad_health(self):
        databases = dict(settings.DATABASES)
        databases['reporting'] = {}
        with self.override_database_connections(databases):
            self.assert_database_health('UNAVAILABLE', analytics_db_status='UNAVAILABLE', status_code=503)

    @override_settings(ANALYTICS_DATABASE_V1='reporting_v1')
    def test_v1_db_bad_health(self):
        databases = dict(settings.DATABASES)
        databases['reporting_v1'] = {}
        with self.override_database_connections(databases):
            self.assert_database_health('UNAVAILABLE', analytics_db_status='UNAVAILABLE', status_code=503)
