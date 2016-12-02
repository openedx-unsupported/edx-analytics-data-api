import datetime
from urllib import urlencode

import ddt
from django_dynamic_fixture import G
import pytz

from django.conf import settings

from analytics_data_api.constants import enrollment_modes
from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.tests.views import CourseSamples, VerifyCourseIdMixin
from analyticsdataserver.tests import TestCaseWithAuthentication


@ddt.ddt
class CourseSummariesViewTests(VerifyCourseIdMixin, TestCaseWithAuthentication):
    model = models.CourseMetaSummaryEnrollment
    serializer = serializers.CourseMetaSummaryEnrollmentSerializer
    expected_summaries = []

    def setUp(self):
        super(CourseSummariesViewTests, self).setUp()
        self.now = datetime.datetime.utcnow()

    def tearDown(self):
        self.model.objects.all().delete()

    def path(self, course_ids=None, fields=None):
        query_params = {}
        for query_arg, data in zip(['course_ids', 'fields'], [course_ids, fields]):
            if data:
                query_params[query_arg] = ','.join(data)
        query_string = '?{}'.format(urlencode(query_params))
        return '/api/v0/course_summaries/{}'.format(query_string)

    def generate_data(self, course_ids=None, modes=None):
        """Generate course summary data for """
        if course_ids is None:
            course_ids = CourseSamples.course_ids

        if modes is None:
            modes = enrollment_modes.ALL

        for course_id in course_ids:
            for mode in modes:
                G(self.model, course_id=course_id, catalog_course_title='Title', catalog_course='Catalog',
                  start_date=datetime.datetime(2016, 10, 11, tzinfo=pytz.utc),
                  end_date=datetime.datetime(2016, 12, 18, tzinfo=pytz.utc),
                  pacing_type='instructor', availability='current', mode=mode,
                  count=5, cumulative_count=10, count_change_7_days=1, create=self.now,)

    def expected_summary(self, course_id, modes=None):
        """Expected summary information for a course and modes to populate with data."""
        if modes is None:
            modes = enrollment_modes.ALL

        num_modes = len(modes)
        count_factor = 5
        cumulative_count_factor = 10
        count_change_factor = 1
        summary = {
            'course_id': course_id,
            'catalog_course_title': 'Title',
            'catalog_course': 'Catalog',
            'start_date': datetime.datetime(2016, 10, 11, tzinfo=pytz.utc).strftime(settings.DATETIME_FORMAT),
            'end_date': datetime.datetime(2016, 12, 18, tzinfo=pytz.utc).strftime(settings.DATETIME_FORMAT),
            'pacing_type': 'instructor',
            'availability': 'current',
            'modes': {},
            'count': count_factor * num_modes,
            'cumulative_count': cumulative_count_factor * num_modes,
            'count_change_7_days': count_change_factor * num_modes,
            'created': self.now.strftime(settings.DATETIME_FORMAT),
        }
        summary['modes'].update({
            mode: {
                'count': count_factor,
                'cumulative_count': cumulative_count_factor,
                'count_change_7_days': count_change_factor,
            } for mode in modes
        })
        summary['modes'].update({
            mode: {
                'count': 0,
                'cumulative_count': 0,
                'count_change_7_days': 0,
            } for mode in set(enrollment_modes.ALL) - set(modes)
        })
        no_prof = summary['modes'].pop(enrollment_modes.PROFESSIONAL_NO_ID)
        prof = summary['modes'].get(enrollment_modes.PROFESSIONAL)
        prof.update({
            'count': prof['count'] + no_prof['count'],
            'cumulative_count': prof['cumulative_count'] + no_prof['cumulative_count'],
            'count_change_7_days': prof['count_change_7_days'] + no_prof['count_change_7_days'],
        })
        return summary

    def all_expected_summaries(self, modes=None):
        if modes is None:
            modes = enrollment_modes.ALL
        return [self.expected_summary(course_id, modes) for course_id in CourseSamples.course_ids]

    @ddt.data(
        None,
        CourseSamples.course_ids,
        ['not/real/course'].extend(CourseSamples.course_ids),
    )
    def test_all_courses(self, course_ids):
        self.generate_data()
        response = self.authenticated_get(self.path(course_ids=course_ids))
        self.assertEquals(response.status_code, 200)
        self.assertItemsEqual(response.data, self.all_expected_summaries())

    @ddt.data(*CourseSamples.course_ids)
    def test_one_course(self, course_id):
        self.generate_data()
        response = self.authenticated_get(self.path(course_ids=[course_id]))
        self.assertEquals(response.status_code, 200)
        self.assertItemsEqual(response.data, [self.expected_summary(course_id)])

    @ddt.data(
        ['availability'],
        ['modes', 'course_id'],
    )
    def test_fields(self, fields):
        self.generate_data()
        response = self.authenticated_get(self.path(fields=fields))
        self.assertEquals(response.status_code, 200)

        # remove fields not requested from expected results
        expected_summaries = self.all_expected_summaries()
        for expected_summary in expected_summaries:
            for field_to_remove in set(expected_summary.keys()) - set(fields):
                expected_summary.pop(field_to_remove)

        self.assertItemsEqual(response.data, expected_summaries)

    @ddt.data(
        [enrollment_modes.VERIFIED],
        [enrollment_modes.HONOR, enrollment_modes.PROFESSIONAL],
    )
    def test_empty_modes(self, modes):
        self.generate_data(modes=modes)
        response = self.authenticated_get(self.path())
        self.assertEquals(response.status_code, 200)
        self.assertItemsEqual(response.data, self.all_expected_summaries(modes))

    def test_no_summaries(self):
        response = self.authenticated_get(self.path())
        self.assertEquals(response.status_code, 404)

    def test_no_matching_courses(self):
        self.generate_data()
        response = self.authenticated_get(self.path(course_ids=['no/course/found']))
        self.assertEquals(response.status_code, 404)

    @ddt.data(
        ['malformed-course-id'],
        [CourseSamples.course_ids[0], 'malformed-course-id'],
    )
    def test_bad_course_id(self, course_ids):
        response = self.authenticated_get(self.path(course_ids=course_ids))
        self.verify_bad_course_id(response)
