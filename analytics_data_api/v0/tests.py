from contextlib import contextmanager
from datetime import datetime
from functools import partial
import random

from django.conf import settings
from django.contrib.auth.models import User
from django.db.utils import ConnectionHandler, DatabaseError
from django.test import TestCase
from django.test.utils import override_settings
from django_dynamic_fixture import G
from mock import patch, Mock
import mock
import pytz
from rest_framework.authtoken.models import Token
from analytics_data_api.v0.models import CourseEnrollmentByBirthYear, CourseEnrollmentByEducation, EducationLevel


# NOTE: Full URLs are used throughout these tests to ensure that the API contract is fulfilled. The URLs should *not*
# change for versions greater than 1.0.0. Tests target a specific version of the API, additional tests should be added
# for subsequent versions if there are breaking changes introduced in those versions.

class TestCaseWithAuthentication(TestCase):
    def setUp(self):
        super(TestCaseWithAuthentication, self).setUp()
        test_user = User.objects.create_user('tester', 'test@example.com', 'testpassword')
        token = Token.objects.create(user=test_user)
        self.authenticated_get = partial(self.client.get, HTTP_AUTHORIZATION='Token ' + token.key)


@contextmanager
def no_database():
    cursor_mock = Mock(side_effect=DatabaseError)
    with mock.patch("django.db.backends.util.CursorWrapper", cursor_mock):
        yield


class OperationalEndpointsTest(TestCaseWithAuthentication):
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

    @staticmethod
    @contextmanager
    def override_database_connections(databases):
        with patch('analytics_data_api.v0.views.connections', ConnectionHandler(databases)):
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


class CourseActivityLastWeekTest(TestCaseWithAuthentication):
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


class CourseEnrollmentViewTestCase(object):
    model = None
    path = None

    def test_get_not_found(self):
        """
        Requests made against non-existent courses should return a 404
        """
        course_id = random.randint(1, 9999)
        self.assertFalse(self.model.objects.filter(course_id=course_id).exists())
        response = self.authenticated_get('/api/v0/courses/%s%s' % (course_id, self.path))
        self.assertEquals(response.status_code, 404)

    def test_get(self):
        raise NotImplementedError


class CourseEnrollmentByBirthYearViewTests(TestCaseWithAuthentication, CourseEnrollmentViewTestCase):
    path = '/enrollment/birth_year'
    model = CourseEnrollmentByBirthYear

    @classmethod
    def setUpClass(cls):
        cls.course_id = 1
        cls.ce1 = G(CourseEnrollmentByBirthYear, course_id=cls.course_id, birth_year=1956)
        cls.ce2 = G(CourseEnrollmentByBirthYear, course_id=cls.course_id, birth_year=1986)

    def test_get(self):
        response = self.authenticated_get('/api/v0/courses/%s%s' % (self.course_id, self.path,))
        self.assertEquals(response.status_code, 200)

        expected = {
            self.ce1.birth_year: self.ce1.num_enrolled_students,
            self.ce2.birth_year: self.ce2.num_enrolled_students,
        }
        actual = response.data['birth_years']
        self.assertEquals(actual, expected)


class CourseEnrollmentByEducationViewTests(TestCaseWithAuthentication, CourseEnrollmentViewTestCase):
    path = '/enrollment/education'
    model = CourseEnrollmentByEducation

    @classmethod
    def setUpClass(cls):
        cls.el1 = G(EducationLevel, name="Doctorate", short_name="doctorate")
        cls.el2 = G(EducationLevel, name="Top Secret", short_name="top_secret")
        cls.course_id = 1
        cls.ce1 = G(CourseEnrollmentByEducation, course_id=cls.course_id, education_level=cls.el1)
        cls.ce2 = G(CourseEnrollmentByEducation, course_id=cls.course_id, education_level=cls.el2)

    def test_get(self):
        response = self.authenticated_get('/api/v0/courses/%s%s' % (self.course_id, self.path,))
        self.assertEquals(response.status_code, 200)

        expected = {
            self.ce1.education_level.short_name: self.ce1.num_enrolled_students,
            self.ce2.education_level.short_name: self.ce2.num_enrolled_students,
        }
        actual = response.data['education_levels']
        self.assertEquals(actual, expected)
