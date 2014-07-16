# NOTE: Full URLs are used throughout these tests to ensure that the API contract is fulfilled. The URLs should *not*
# change for versions greater than 1.0.0. Tests target a specific version of the API, additional tests should be added
# for subsequent versions if there are breaking changes introduced in those versions.

import datetime
import random

from django.conf import settings
from django_dynamic_fixture import G
import pytz

from analytics_data_api.v0.models import CourseEnrollmentByBirthYear, CourseEnrollmentByEducation, EducationLevel, \
    CourseEnrollmentByGender, CourseActivityByWeek, Course, ProblemResponseAnswerDistribution, CourseEnrollmentDaily, \
    Country, \
    CourseEnrollmentByCountry
from analytics_data_api.v0.serializers import ProblemResponseAnswerDistributionSerializer
from analyticsdataserver.tests import TestCaseWithAuthentication


class CourseActivityLastWeekTest(TestCaseWithAuthentication):
    def setUp(self):
        super(CourseActivityLastWeekTest, self).setUp()
        self.course_id = 'edX/DemoX/Demo_Course'
        self.course = G(Course, course_id=self.course_id)
        interval_start = '2014-05-24T00:00:00Z'
        interval_end = '2014-06-01T00:00:00Z'
        G(CourseActivityByWeek, course=self.course, interval_start=interval_start, interval_end=interval_end,
          activity_type='posted_forum', count=100)
        G(CourseActivityByWeek, course=self.course, interval_start=interval_start, interval_end=interval_end,
          activity_type='attempted_problem', count=200)
        G(CourseActivityByWeek, course=self.course, interval_start=interval_start, interval_end=interval_end,
          activity_type='any', count=300)
        G(CourseActivityByWeek, course=self.course, interval_start=interval_start, interval_end=interval_end,
          activity_type='played_video', count=400)

    def test_activity(self):
        response = self.authenticated_get('/api/v0/courses/{0}/recent_activity'.format(self.course_id))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record())

    @staticmethod
    def get_activity_record(**kwargs):
        default = {
            'course_id': 'edX/DemoX/Demo_Course',
            'interval_start': datetime.datetime(2014, 5, 24, 0, 0, tzinfo=pytz.utc),
            'interval_end': datetime.datetime(2014, 6, 1, 0, 0, tzinfo=pytz.utc),
            'activity_type': 'any',
            'count': 300,
        }
        default.update(kwargs)
        return default

    def test_activity_auth(self):
        response = self.client.get('/api/v0/courses/{0}/recent_activity'.format(self.course_id), follow=True)
        self.assertEquals(response.status_code, 401)

    def test_url_encoded_course_id(self):
        response = self.authenticated_get('/api/v0/courses/edX%2FDemoX%2FDemo_Course/recent_activity')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record())

    def test_video_activity(self):
        activity_type = 'played_video'
        response = self.authenticated_get('/api/v0/courses/{0}/recent_activity?activity_type={1}'.format(
            self.course_id, activity_type))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record(activity_type=activity_type, count=400))

    def test_unknown_activity(self):
        activity_type = 'missing_activity_type'
        response = self.authenticated_get('/api/v0/courses/{0}/recent_activity?activity_type={1}'.format(
            self.course_id, activity_type))
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

    def _get_non_existent_course_id(self):
        course_id = random.randint(100, 9999)

        if not Course.objects.filter(course_id=course_id).exists():
            return course_id

        return self._get_non_existent_course_id()

    def test_get_not_found(self):
        """ Requests made against non-existent courses should return a 404 """
        course_id = self._get_non_existent_course_id()
        self.assertFalse(self.model.objects.filter(course__course_id=course_id).exists())  # pylint: disable=no-member
        response = self.authenticated_get('/api/v0/courses/%s%s' % (course_id, self.path))  # pylint: disable=no-member
        self.assertEquals(response.status_code, 404)  # pylint: disable=no-member

    def test_get(self):
        raise NotImplementedError


class CourseEnrollmentByBirthYearViewTests(TestCaseWithAuthentication, CourseEnrollmentViewTestCase):
    path = '/enrollment/birth_year'
    model = CourseEnrollmentByBirthYear

    @classmethod
    def setUpClass(cls):
        cls.course = G(Course)
        cls.ce1 = G(CourseEnrollmentByBirthYear, course=cls.course, birth_year=1956)
        cls.ce2 = G(CourseEnrollmentByBirthYear, course=cls.course, birth_year=1986)

    def test_get(self):
        response = self.authenticated_get('/api/v0/courses/%s%s' % (self.course.course_id, self.path,))
        self.assertEquals(response.status_code, 200)

        expected = {
            self.ce1.birth_year: self.ce1.count,
            self.ce2.birth_year: self.ce2.count,
        }
        actual = response.data['birth_years']
        self.assertEquals(actual, expected)


class CourseEnrollmentByEducationViewTests(TestCaseWithAuthentication, CourseEnrollmentViewTestCase):
    path = '/enrollment/education'
    model = CourseEnrollmentByEducation

    @classmethod
    def setUpClass(cls):
        cls.el1 = G(EducationLevel, name='Doctorate', short_name='doctorate')
        cls.el2 = G(EducationLevel, name='Top Secret', short_name='top_secret')
        cls.course = G(Course)
        cls.ce1 = G(CourseEnrollmentByEducation, course=cls.course, education_level=cls.el1)
        cls.ce2 = G(CourseEnrollmentByEducation, course=cls.course, education_level=cls.el2)

    def test_get(self):
        response = self.authenticated_get('/api/v0/courses/%s%s' % (self.course.course_id, self.path,))
        self.assertEquals(response.status_code, 200)

        expected = {
            self.ce1.education_level.short_name: self.ce1.count,
            self.ce2.education_level.short_name: self.ce2.count,
        }
        actual = response.data['education_levels']
        self.assertEquals(actual, expected)


class CourseEnrollmentByGenderViewTests(TestCaseWithAuthentication, CourseEnrollmentViewTestCase):
    path = '/enrollment/gender'
    model = CourseEnrollmentByGender

    @classmethod
    def setUpClass(cls):
        cls.course = G(Course)
        cls.ce1 = G(CourseEnrollmentByGender, course=cls.course, gender='m')
        cls.ce2 = G(CourseEnrollmentByGender, course=cls.course, gender='f')

    def test_get(self):
        response = self.authenticated_get('/api/v0/courses/%s%s' % (self.course.course_id, self.path,))
        self.assertEquals(response.status_code, 200)

        expected = {
            self.ce1.gender: self.ce1.count,
            self.ce2.gender: self.ce2.count,
        }
        actual = response.data['genders']
        self.assertEquals(actual, expected)


# pylint: disable=no-member,no-value-for-parameter
class AnswerDistributionTests(TestCaseWithAuthentication):
    path = '/answer_distribution'
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.course_id = "org/num/run"
        cls.module_id = "i4x://org/num/run/problem/RANDOMNUMBER"
        cls.part_id1 = "i4x-org-num-run-problem-RANDOMNUMBER_2_1"
        cls.ad1 = G(
            ProblemResponseAnswerDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id,
            part_id=cls.part_id1
        )

    def test_get(self):
        response = self.authenticated_get('/api/v0/problems/%s%s' % (self.module_id, self.path))
        self.assertEquals(response.status_code, 200)

        expected_dict = ProblemResponseAnswerDistributionSerializer(self.ad1).data
        actual_list = response.data
        self.assertEquals(len(actual_list), 1)
        self.assertDictEqual(actual_list[0], expected_dict)

    def test_get_404(self):
        response = self.authenticated_get('/api/v0/problems/%s%s' % ("DOES-NOT-EXIST", self.path))
        self.assertEquals(response.status_code, 404)


class CourseEnrollmentLatestViewTests(TestCaseWithAuthentication, CourseEnrollmentViewTestCase):
    model = CourseEnrollmentDaily
    path = '/enrollment'

    @classmethod
    def setUpClass(cls):
        cls.course = G(Course)
        cls.ce = G(CourseEnrollmentDaily, course=cls.course, date=datetime.date(2014, 1, 1), count=203)

    def test_get(self):
        response = self.authenticated_get('/api/v0/courses/%s%s' % (self.course.course_id, self.path,))
        self.assertEquals(response.status_code, 200)
        expected = {'course_id': self.ce.course.course_id, 'count': self.ce.count, 'date': self.ce.date}
        self.assertDictEqual(response.data, expected)


class CourseEnrollmentByLocationViewTests(TestCaseWithAuthentication, CourseEnrollmentViewTestCase):
    path = '/enrollment/location/'
    model = CourseEnrollmentByCountry

    def get_expected_response(self, *args):
        return [{'course_id': ce.course.course_id, 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
                 'country': {'code': ce.country.code, 'name': ce.country.name}} for ce in args]

    def test_get(self):
        course = G(Course)
        date1 = datetime.date(2014, 1, 1)
        date2 = datetime.date(2013, 1, 1)
        ce1 = G(CourseEnrollmentByCountry, course=course, country=G(Country), count=455, date=date1)
        ce2 = G(CourseEnrollmentByCountry, course=course, country=G(Country), count=356, date=date1)

        # This should not be returned as the view should return only the latest data when no interval is supplied.
        G(CourseEnrollmentByCountry, course=course, country=G(Country), count=12, date=date2)

        response = self.authenticated_get('/api/v0/courses/%s%s' % (course.course_id, self.path,))
        self.assertEquals(response.status_code, 200)

        expected = self.get_expected_response(ce1, ce2)
        self.assertListEqual(response.data, expected)

    def test_get_with_intervals(self):
        course = G(Course)
        country1 = G(Country)
        country2 = G(Country)
        date = datetime.date(2014, 1, 1)
        ce1 = G(CourseEnrollmentByCountry, course=course, country=country1, date=date)
        ce2 = G(CourseEnrollmentByCountry, course=course, country=country2, date=date)

        # If start date is after date of existing data, no data should be returned
        response = self.authenticated_get('/api/v0/courses/%s%s?start_date=2014-02-01' % (course.course_id, self.path,))
        self.assertEquals(response.status_code, 200)
        self.assertListEqual([], response.data)

        # If end date is before date of existing data, no data should be returned
        response = self.authenticated_get('/api/v0/courses/%s%s?end_date=2013-02-01' % (course.course_id, self.path,))
        self.assertEquals(response.status_code, 200)
        self.assertListEqual([], response.data)

        # If data falls in date range, data should be returned
        response = self.authenticated_get(
            '/api/v0/courses/%s%s?start_date=2013-02-01&end_date=2014-02-01' % (course.course_id, self.path,))
        self.assertEquals(response.status_code, 200)
        expected = self.get_expected_response(ce1, ce2)
        self.assertListEqual(response.data, expected)
