from contextlib import contextmanager
from functools import partial

from django.conf import settings
from django.contrib.auth.models import User
from django.db.utils import ConnectionHandler, DatabaseError
from django.test import TestCase
from django.test.utils import override_settings
from mock import patch, Mock
import mock
from rest_framework.authtoken.models import Token


class TestCaseWithAuthentication(TestCase):
    def setUp(self):
        super(TestCaseWithAuthentication, self).setUp()
        test_user = User.objects.create_user('tester', 'test@example.com', 'testpassword')
        token = Token.objects.create(user=test_user)
        self.authenticated_get = partial(self.client.get, HTTP_AUTHORIZATION='Token ' + token.key, follow=True)


@contextmanager
def no_database():
    cursor_mock = Mock(side_effect=DatabaseError)
    with mock.patch('django.db.backends.util.CursorWrapper', cursor_mock):
        yield


class OperationalEndpointsTest(TestCaseWithAuthentication):
    def test_status(self):
        response = self.client.get('/status', follow=True)
        self.assertEquals(response.status_code, 200)

    def test_authentication_check_failure(self):
        response = self.client.get('/authenticated', follow=True)
        self.assertEquals(response.status_code, 401)

    def test_authentication_check_success(self):
        response = self.authenticated_get('/authenticated', follow=True)
        self.assertEquals(response.status_code, 200)

    def test_health(self):
        self.assert_database_health('OK')

    def assert_database_health(self, status):
        response = self.client.get('/health', follow=True)
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

    @staticmethod
    @contextmanager
    def override_database_connections(databases):
        with patch('analyticsdataserver.views.connections', ConnectionHandler(databases)):
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
