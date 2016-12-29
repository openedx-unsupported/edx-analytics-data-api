import json
import logging
from contextlib import contextmanager

import mock
import responses

from django.conf import settings
from django.contrib.auth.models import User
from django.db.utils import ConnectionHandler, DatabaseError
from django.test import TestCase
from django.test.utils import override_settings
from rest_framework.authtoken.models import Token

from analytics_data_api.v0.models import CourseEnrollmentDaily, CourseEnrollmentByBirthYear
from analyticsdataserver.clients import CourseBlocksApiClient
from analyticsdataserver.router import AnalyticsApiRouter
from analyticsdataserver.utils import temp_log_level


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


class UtilsTests(TestCase):
    def setUp(self):
        self.logger = logging.getLogger('test_logger')

    def test_temp_log_level(self):
        """Ensures log level is adjusted within context manager and returns to original level when exited."""
        original_level = self.logger.getEffectiveLevel()
        with temp_log_level('test_logger'):  # NOTE: defaults to logging.CRITICAL
            self.assertEqual(self.logger.getEffectiveLevel(), logging.CRITICAL)
        self.assertEqual(self.logger.getEffectiveLevel(), original_level)

        # test with log_level option used
        with temp_log_level('test_logger', log_level=logging.DEBUG):
            self.assertEqual(self.logger.getEffectiveLevel(), logging.DEBUG)
        self.assertEqual(self.logger.getEffectiveLevel(), original_level)


class ClientTests(TestCase):
    @mock.patch('analyticsdataserver.clients.EdxRestApiClient')
    def setUp(self, *args, **kwargs):  # pylint: disable=unused-argument
        self.client = CourseBlocksApiClient('http://example.com/', 'token', 5)

    @responses.activate
    def test_all_videos(self):
        responses.add(responses.GET, 'http://example.com/blocks/', body=json.dumps({'blocks': {
            'block-v1:edX+DemoX+Demo_Course+type@video+block@5c90cffecd9b48b188cbfea176bf7fe9': {
                'id': 'block-v1:edX+DemoX+Demo_Course+type@video+block@5c90cffecd9b48b188cbfea176bf7fe9'
            },
            'block-v1:edX+DemoX+Demo_Course+type@video+block@7e9b434e6de3435ab99bd3fb25bde807': {
                'id': 'block-v1:edX+DemoX+Demo_Course+type@video+block@7e9b434e6de3435ab99bd3fb25bde807'
            }
        }}), status=200, content_type='application/json')
        videos = self.client.all_videos('course_id')
        self.assertListEqual(videos, [
            {
                'video_id': 'course_id|5c90cffecd9b48b188cbfea176bf7fe9',
                'video_module_id': '5c90cffecd9b48b188cbfea176bf7fe9'
            },
            {
                'video_id': 'course_id|7e9b434e6de3435ab99bd3fb25bde807',
                'video_module_id': '7e9b434e6de3435ab99bd3fb25bde807'
            }
        ])

    @responses.activate
    @mock.patch('analyticsdataserver.clients.logger')
    def test_all_videos_401(self, logger):
        responses.add(responses.GET, 'http://example.com/blocks/', status=401, content_type='application/json')
        videos = self.client.all_videos('course_id')
        logger.warning.assert_called_with(
            'Course Blocks API failed to return video ids (%s). ' +
            'See README for instructions on how to authenticate the API with your local LMS.', 401)
        self.assertEqual(videos, None)

    @responses.activate
    @mock.patch('analyticsdataserver.clients.logger')
    def test_all_videos_404(self, logger):
        responses.add(responses.GET, 'http://example.com/blocks/', status=404, content_type='application/json')
        videos = self.client.all_videos('course_id')
        logger.warning.assert_called_with('Course Blocks API failed to return video ids (%s). ' +
                                          'Does the course exist in the LMS?', 404)
        self.assertEqual(videos, None)

    @responses.activate
    @mock.patch('analyticsdataserver.clients.logger')
    def test_all_videos_500(self, logger):
        responses.add(responses.GET, 'http://example.com/blocks/', status=418, content_type='application/json')
        videos = self.client.all_videos('course_id')
        logger.warning.assert_called_with('Course Blocks API failed to return video ids (%s).', 418)
        self.assertEqual(videos, None)

    @responses.activate
    def test_all_videos_pass_through_bad_id(self):
        responses.add(responses.GET, 'http://example.com/blocks/', body=json.dumps({'blocks': {
            'block-v1:edX+DemoX+Demo_Course+type@video+block@5c90cffecd9b48b188cbfea176bf7fe9': {
                'id': 'bad_key'
            },
            'block-v1:edX+DemoX+Demo_Course+type@video+block@7e9b434e6de3435ab99bd3fb25bde807': {
                'id': 'bad_key'
            }
        }}), status=200, content_type='application/json')
        responses.add(responses.GET, 'http://example.com/blocks/', status=200, content_type='application/json')
        videos = self.client.all_videos('course_id')
        self.assertListEqual(videos, [
            {
                'video_id': 'course_id|bad_key',
                'video_module_id': 'bad_key'
            },
            {
                'video_id': 'course_id|bad_key',
                'video_module_id': 'bad_key'
            }
        ])
