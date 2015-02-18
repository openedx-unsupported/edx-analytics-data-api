from contextlib import contextmanager

from django.conf import settings
from django.contrib.auth.models import User
from django.db.utils import ConnectionHandler, DatabaseError
from django.test import TestCase
from django.test.utils import override_settings

import mock
from rest_framework.authtoken.models import Token
from analytics_data_api.v0.models import CourseEnrollmentDaily, CourseEnrollmentByBirthYear
from analyticsdataserver.router import AnalyticsApiRouter


class TestCaseWithAuthentication(TestCase):
    def setUp(self):
        super(TestCaseWithAuthentication, self).setUp()
        test_user = User.objects.create_user('tester', 'test@example.com', 'testpassword')
        self.token = Token.objects.create(user=test_user)

    def authenticated_get(self, path, data=None, follow=True, **extra):
        data = data or {}
        return self.client.get(path, data, follow, HTTP_AUTHORIZATION='Token ' + self.token.key, **extra)


@contextmanager
def no_database():
    cursor_mock = mock.Mock(side_effect=DatabaseError)
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

    def assert_database_health(self, status, status_code=200):
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
        self.assertEquals(response.status_code, status_code)

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


class AnalyticsApiRouterTests(TestCase):
    def setUp(self):
        self.router = AnalyticsApiRouter()

    def test_allow_relation(self):
        """
        Relations should only be allowed for objects contained within the same database.
        """
        self.assertFalse(self.router.allow_relation(CourseEnrollmentDaily, User))
        self.assertTrue(self.router.allow_relation(CourseEnrollmentDaily, CourseEnrollmentByBirthYear))
