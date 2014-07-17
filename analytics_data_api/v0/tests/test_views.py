# NOTE: Full URLs are used throughout these tests to ensure that the API contract is fulfilled. The URLs should *not*
# change for versions greater than 1.0.0. Tests target a specific version of the API, additional tests should be added
# for subsequent versions if there are breaking changes introduced in those versions.
import StringIO
import csv

import datetime
import random

from django.conf import settings
from django_dynamic_fixture import G
import pytz

from analytics_data_api.v0 import models
from analytics_data_api.v0.serializers import ProblemResponseAnswerDistributionSerializer
from analyticsdataserver.tests import TestCaseWithAuthentication


class CourseActivityLastWeekTest(TestCaseWithAuthentication):
    def setUp(self):
        super(CourseActivityLastWeekTest, self).setUp()
        self.course_id = 'edX/DemoX/Demo_Course'
        self.course = G(models.Course, course_id=self.course_id)
        interval_start = '2014-05-24T00:00:00Z'
        interval_end = '2014-06-01T00:00:00Z'
        G(models.CourseActivityByWeek, course=self.course, interval_start=interval_start, interval_end=interval_end,
          activity_type='posted_forum', count=100)
        G(models.CourseActivityByWeek, course=self.course, interval_start=interval_start, interval_end=interval_end,
          activity_type='attempted_problem', count=200)
        G(models.CourseActivityByWeek, course=self.course, interval_start=interval_start, interval_end=interval_end,
          activity_type='any', count=300)
        G(models.CourseActivityByWeek, course=self.course, interval_start=interval_start, interval_end=interval_end,
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


# pylint: disable=no-member
class CourseEnrollmentViewTestCase(object):
    model = None
    path = None

    def _get_non_existent_course_id(self):
        course_id = random.randint(100, 9999)

        if not models.Course.objects.filter(course_id=course_id).exists():
            return course_id

        return self._get_non_existent_course_id()

    def get_expected_response(self, *args):
        raise NotImplementedError

    def test_get_not_found(self):
        """ Requests made against non-existent courses should return a 404 """
        course_id = self._get_non_existent_course_id()
        self.assertFalse(self.model.objects.filter(course__course_id=course_id).exists())
        response = self.authenticated_get('/api/v0/courses/%s%s' % (course_id, self.path))
        self.assertEquals(response.status_code, 404)

    def test_get(self):
        # Validate the basic response status
        response = self.authenticated_get('/api/v0/courses/%s%s' % (self.course.course_id, self.path,))
        self.assertEquals(response.status_code, 200)

        # Validate the actual data
        expected = self.get_expected_response(*self.model.objects.filter(date=self.date))
        self.assertEquals(response.data, expected)

    def test_get_csv(self):
        path = '/api/v0/courses/%s%s' % (self.course.course_id, self.path,)
        csv_content_type = 'text/csv'
        response = self.authenticated_get(path, HTTP_ACCEPT=csv_content_type)

        # Validate the basic response status and content code
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'].split(';')[0], csv_content_type)

        # Validate the actual data
        expected = self.get_expected_response(*self.model.objects.filter(date=self.date))
        reader = csv.DictReader(StringIO.StringIO(response.content))
        actual = list(reader)

        for actual_dict in actual:
            for key, value in actual_dict.items():
                # Adding "birth_year" here is not perfect, but it's such a limited case that it doesn't necessarily
                # warrant making this functionality extensible to all sub classes.
                if key in ('count', 'birth_year'):
                    actual_dict[key] = int(actual_dict[key])

                if '.' in key:
                    parent, child = key.split('.')

                    if parent not in actual_dict:
                        actual_dict[parent] = {}

                    actual_dict[parent][child] = value
                    actual_dict.pop(key, None)

        self.assertListEqual(actual, expected)

    def test_get_with_intervals(self):
        expected = self.get_expected_response(*self.model.objects.filter(date=self.date))
        self.assertIntervalFilteringWorks(expected, self.date, self.date + datetime.timedelta(days=1))

    def assertIntervalFilteringWorks(self, expected_response, start_date, end_date):
        course = self.course

        # If start date is after date of existing data, no data should be returned
        date = (start_date + datetime.timedelta(days=30)).strftime(settings.DATE_FORMAT)
        response = self.authenticated_get('/api/v0/courses/%s%s?start_date=%s' % (course.course_id, self.path, date))
        self.assertEquals(response.status_code, 200)
        self.assertListEqual([], response.data)

        # If end date is before date of existing data, no data should be returned
        date = (start_date - datetime.timedelta(days=30)).strftime(settings.DATE_FORMAT)
        response = self.authenticated_get('/api/v0/courses/%s%s?end_date=%s' % (course.course_id, self.path, date))
        self.assertEquals(response.status_code, 200)
        self.assertListEqual([], response.data)

        # If data falls in date range, data should be returned
        start_date = start_date.strftime(settings.DATE_FORMAT)
        end_date = end_date.strftime(settings.DATE_FORMAT)
        response = self.authenticated_get(
            '/api/v0/courses/%s%s?start_date=%s&end_date=%s' % (course.course_id, self.path, start_date, end_date))
        self.assertEquals(response.status_code, 200)
        self.assertListEqual(response.data, expected_response)


class CourseEnrollmentByBirthYearViewTests(TestCaseWithAuthentication, CourseEnrollmentViewTestCase):
    path = '/enrollment/birth_year'
    model = models.CourseEnrollmentByBirthYear

    @classmethod
    def setUpClass(cls):
        cls.course = G(models.Course)
        cls.date = datetime.date(2014, 1, 1)
        G(cls.model, course=cls.course, date=cls.date, birth_year=1956)
        G(cls.model, course=cls.course, date=cls.date, birth_year=1986)
        G(cls.model, course=cls.course, date=cls.date - datetime.timedelta(days=10), birth_year=1956)
        G(cls.model, course=cls.course, date=cls.date - datetime.timedelta(days=10), birth_year=1986)

    def get_expected_response(self, *args):
        return [
            {'course_id': str(ce.course.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'birth_year': ce.birth_year} for ce in args]

    def test_get(self):
        response = self.authenticated_get('/api/v0/courses/%s%s' % (self.course.course_id, self.path,))
        self.assertEquals(response.status_code, 200)

        expected = self.get_expected_response(*self.model.objects.filter(date=self.date))
        self.assertEquals(response.data, expected)

    def test_get_with_intervals(self):
        expected = self.get_expected_response(*self.model.objects.filter(date=self.date))
        self.assertIntervalFilteringWorks(expected, self.date, self.date + datetime.timedelta(days=1))


class CourseEnrollmentByEducationViewTests(TestCaseWithAuthentication, CourseEnrollmentViewTestCase):
    path = '/enrollment/education/'
    model = models.CourseEnrollmentByEducation

    @classmethod
    def setUpClass(cls):
        cls.el1 = G(models.EducationLevel, name='Doctorate', short_name='doctorate')
        cls.el2 = G(models.EducationLevel, name='Top Secret', short_name='top_secret')
        cls.course = G(models.Course)
        cls.date = datetime.date(2014, 1, 1)
        G(cls.model, course=cls.course, date=cls.date, education_level=cls.el1)
        G(cls.model, course=cls.course, date=cls.date, education_level=cls.el2)
        G(cls.model, course=cls.course, date=cls.date - datetime.timedelta(days=2),
          education_level=cls.el2)

    def get_expected_response(self, *args):
        return [
            {'course_id': str(ce.course.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'education_level': {'name': ce.education_level.name, 'short_name': ce.education_level.short_name}} for
            ce in args]


class CourseEnrollmentByGenderViewTests(TestCaseWithAuthentication, CourseEnrollmentViewTestCase):
    path = '/enrollment/gender/'
    model = models.CourseEnrollmentByGender

    @classmethod
    def setUpClass(cls):
        cls.course = G(models.Course)
        cls.date = datetime.date(2014, 1, 1)
        G(cls.model, course=cls.course, gender='m', date=cls.date, count=34)
        G(cls.model, course=cls.course, gender='f', date=cls.date, count=45)
        G(cls.model, course=cls.course, gender='f', date=cls.date - datetime.timedelta(days=2), count=45)

    def get_expected_response(self, *args):
        return [
            {'course_id': str(ce.course.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'gender': ce.gender} for ce in args]


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
            models.ProblemResponseAnswerDistribution,
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


class CourseEnrollmentViewTests(TestCaseWithAuthentication, CourseEnrollmentViewTestCase):
    model = models.CourseEnrollmentDaily
    path = '/enrollment'

    @classmethod
    def setUpClass(cls):
        cls.course = G(models.Course)
        cls.date = datetime.date(2014, 1, 1)
        G(cls.model, course=cls.course, date=cls.date, count=203)
        G(cls.model, course=cls.course, date=cls.date - datetime.timedelta(days=5), count=203)

    def get_expected_response(self, *args):
        return [
            {'course_id': str(ce.course.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT)}
            for ce in args]


class CourseEnrollmentByLocationViewTests(TestCaseWithAuthentication, CourseEnrollmentViewTestCase):
    path = '/enrollment/location/'
    model = models.CourseEnrollmentByCountry

    def get_expected_response(self, *args):
        return [
            {'course_id': str(ce.course.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'country': {'code': ce.country.code, 'name': ce.country.name}} for ce in args]

    @classmethod
    def setUpClass(cls):
        cls.course = G(models.Course)
        cls.date = datetime.date(2014, 1, 1)
        G(cls.model, course=cls.course, country=G(models.Country), count=455, date=cls.date)
        G(cls.model, course=cls.course, country=G(models.Country), count=356, date=cls.date)
        G(cls.model, course=cls.course, country=G(models.Country), count=12,
          date=cls.date - datetime.timedelta(days=29))
