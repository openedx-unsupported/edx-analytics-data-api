# NOTE: Full URLs are used throughout these tests to ensure that the API contract is fulfilled. The URLs should *not*
# change for versions greater than 1.0.0. Tests target a specific version of the API, additional tests should be added
# for subsequent versions if there are breaking changes introduced in those versions.

from datetime import datetime
import random

from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from django_dynamic_fixture import G
import pytz

from analytics_data_api.v0.models import CourseEnrollmentByBirthYear, CourseEnrollmentByEducation, EducationLevel, \
    CourseEnrollmentByGender, CourseActivityByWeek, Course, ProblemResponseAnswerDistribution
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
            'interval_start': datetime(2014, 5, 24, 0, 0, tzinfo=pytz.utc),
            'interval_end': datetime(2014, 6, 1, 0, 0, tzinfo=pytz.utc),
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
        '''
        Requests made against non-existent courses should return a 404
        '''
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
        cls.el1 = G(EducationLevel, name='Doctorate', short_name='doctorate')
        cls.el2 = G(EducationLevel, name='Top Secret', short_name='top_secret')
        cls.course = G(Course)
        cls.ce1 = G(CourseEnrollmentByEducation, course=cls.course, education_level=cls.el1)
        cls.ce2 = G(CourseEnrollmentByEducation, course=cls.course, education_level=cls.el2)

    def test_get(self):
        response = self.authenticated_get('/api/v0/courses/%s%s' % (self.course.course_id, self.path,))
        self.assertEquals(response.status_code, 200)

        expected = {
            self.ce1.education_level.short_name: self.ce1.num_enrolled_students,
            self.ce2.education_level.short_name: self.ce2.num_enrolled_students,
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
            self.ce1.gender: self.ce1.num_enrolled_students,
            self.ce2.gender: self.ce2.num_enrolled_students,
        }
        actual = response.data['genders']
        self.assertEquals(actual, expected)


class CourseManagerTests(TestCase):
    def test_get_by_natural_key(self):
        course_id = 'edX/DemoX/Demo_Course'
        self.assertRaises(ObjectDoesNotExist, Course.objects.get_by_natural_key, course_id)

        course = G(Course, course_id=course_id)
        self.assertEqual(course, Course.objects.get_by_natural_key(course_id))


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
