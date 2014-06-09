
from contextlib import contextmanager
from datetime import datetime
from functools import partial

from django.conf import settings
from django.contrib.auth.models import User
from django.db.utils import ConnectionHandler
from django.test import TestCase
from django.test.utils import override_settings
from mock import patch
import pytz
from rest_framework.authtoken.models import Token

from analyticsdata.views import handle_internal_server_error, handle_missing_resource_error

# NOTE: Full URLs are used throughout these tests to ensure that the API contract is fulfilled. The URLs should *not*
# change for versions greater than 1.0.0. Tests target a specific version of the API, additional tests should be added
# for subsequent versions if there are breaking changes introduced in those versions.


class TestCaseWithAutenticatation(TestCase):

    def setUp(self):
        super(TestCaseWithAutenticatation, self).setUp()
        test_user = User.objects.create_user('tester', 'test@example.com', 'testpassword')
        token = Token.objects.create(user=test_user)
        self.authenticated_get = partial(self.client.get, HTTP_AUTHORIZATION='Token ' + token.key)


class OperationalEndpointsTest(TestCaseWithAutenticatation):

    def test_status(self):
        response = self.client.get('/api/v0/status')
        self.assertEquals(response.status_code, 200)

    def test_authentication_check_failure(self):
        response = self.client.get('/api/v0/authenticated')
        self.assertEquals(response.status_code, 401)

    def test_authentication_check_success(self):
        response = self.authenticated_get('/api/v0/authenticated')
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


class CourseActivityLastWeekTest(TestCaseWithAutenticatation):

    fixtures = ['single_course_activity']

    COURSE_ID = 'edX/DemoX/Demo_Course'

    def test_activity(self):
        response = self.authenticated_get('/api/v0/courses/{0}/recent_activity'.format(self.COURSE_ID))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record())

    @staticmethod
    def get_activity_record(**kwargs):
        default = {
            'course_id': 'edX/DemoX/Demo_Course',
            'interval_start': datetime(2014, 5, 24, 0, 0, tzinfo=pytz.utc),
            'interval_end': datetime(2014, 6, 1, 0, 0, tzinfo=pytz.utc),
            'label': 'ACTIVE',
            'count': 300,
        }
        default.update(kwargs)
        return default

    def test_activity_auth(self):
        response = self.client.get('/api/v0/courses/{0}/recent_activity'.format(self.COURSE_ID))
        self.assertEquals(response.status_code, 401)

    def test_url_encoded_course_id(self):
        response = self.authenticated_get('/api/v0/courses/edX%2FDemoX%2FDemo_Course/recent_activity')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record())

    def test_video_activity(self):
        label = 'PLAYED_VIDEO'
        response = self.authenticated_get('/api/v0/courses/{0}/recent_activity?label={1}'.format(self.COURSE_ID, label))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record(label=label, count=400))

    def test_unknown_activity(self):
        label = 'MISSING_ACTIVITY_TYPE'
        response = self.authenticated_get('/api/v0/courses/{0}/recent_activity?label={1}'.format(self.COURSE_ID, label))
        self.assertEquals(response.status_code, 404)

    def test_unknown_course_id(self):
        response = self.authenticated_get('/api/v0/courses/{0}/recent_activity'.format('foo'))
        self.assertEquals(response.status_code, 404)

    def test_missing_course_id(self):
        response = self.authenticated_get('/api/v0/courses/recent_activity')
        self.assertEquals(response.status_code, 404)
