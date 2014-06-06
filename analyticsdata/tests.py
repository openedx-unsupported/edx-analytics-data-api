
from contextlib import contextmanager

from django.conf import settings
from django.contrib.auth.models import User
from django.db.utils import ConnectionHandler
from django.test import TestCase
from django.test.utils import override_settings
from mock import patch
from rest_framework.authtoken.models import Token

from analyticsdata.views import handle_internal_server_error, handle_missing_resource_error

# NOTE: Full URLs are used throughout these tests to ensure that the API contract is fulfilled. The URLs should *not*
# change for versions greater than 1.0.0. Tests target a specific version of the API, additional tests should be added
# for subsequent versions if there are breaking changes introduced in those versions.


class OperationalEndpointsTest(TestCase):

    def test_status(self):
        response = self.client.get('/api/v0/status')
        self.assertEquals(response.status_code, 200)

    def test_authentication_check_failure(self):
        response = self.client.get('/api/v0/authenticated')
        self.assertEquals(response.status_code, 401)

    def test_authentication_check_success(self):
        test_user = User.objects.create_user('tester', 'test@example.com', 'testpassword')
        token = Token.objects.create(user=test_user)
        response = self.client.get('/api/v0/authenticated', HTTP_AUTHORIZATION='Token ' + token.key)
        self.assertEquals(response.status_code, 200)

    def test_health(self):
        self.assert_database_health('OK')

    def assert_database_health(self, status):
        response = self.client.get('/api/v0/health')
        self.assertEquals(
            response.data,
            {
                'overall_status': status,
                'detailed_status': {
                    'database_connection': status
                }
            }
        )
        self.assertEquals(response.status_code, 200)

    def test_database_down(self):
        databases = {
            "default": {}
        }
        with self.override_database_connections(databases):
            self.assert_database_health('UNAVAILABLE')

    @staticmethod
    @contextmanager
    def override_database_connections(databases):
        with patch('analyticsdata.views.connections', ConnectionHandler(databases)):
            yield

    @override_settings(ANALYTICS_DATABASE='reporting')
    def test_read_setting(self):
        databases = dict(settings.DATABASES)
        databases['reporting'] = {}

        with self.override_database_connections(databases):
            self.assert_database_health('UNAVAILABLE')

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


class ErrorHandlingTest(TestCase):

    def test_internal_server_error_handling(self):
        response = handle_internal_server_error(None)
        self.validate_error_response(response, 500)

    def validate_error_response(self, response, status_code):
        self.assertEquals(response.content, '{{"status": {0}}}'.format(status_code))
        self.assertEquals(response.status_code, status_code)
        self.assertEquals(response.get('Content-Type'), 'application/json; charset=utf-8')

    def test_missing_resource_handling(self):
        response = handle_missing_resource_error(None)
        self.validate_error_response(response, 404)
