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
        self.maxDiff = None

    def tearDown(self):
        self.model.objects.all().delete()

    def path(self, course_ids=None, fields=None):
        query_params = {}
        for query_arg, data in zip(['course_ids', 'fields'], [course_ids, fields]):
            if data:
                query_params[query_arg] = ','.join(data)
        query_string = '?{}'.format(urlencode(query_params))
        return '/api/v0/course_summaries/{}'.format(query_string)

    def generate_data(self, course_ids=None, modes=None, availability='Current'):
        """Generate course summary data for """
        if course_ids is None:
            course_ids = CourseSamples.course_ids

        if modes is None:
            modes = enrollment_modes.ALL

        for course_id in course_ids:
            for mode in modes:
                G(self.model, course_id=course_id, catalog_course_title='Title', catalog_course='Catalog',
                  start_time=datetime.datetime(2016, 10, 11, tzinfo=pytz.utc),
                  end_time=datetime.datetime(2016, 12, 18, tzinfo=pytz.utc),
                  pacing_type='instructor', availability=availability, enrollment_mode=mode,
                  count=5, cumulative_count=10, count_change_7_days=1, create=self.now,)

    def collapse_nested_dict(self, nested_dict, dot_separated_key):
        """Recursively flatten dictionary to a list of tuples with dot-separated keys and only atomic values.

        For example:
        self.collapse_nested_dict({
            'audit': {
                'count': 5,
                'count_change_7_days': 1,
                ...
            },
            'credit': {
                'count': 10,
                ...
            },
            ...
        }, ['enrollment_modes'])

        Should return:
        [
            ('enrollment_modes.audit.count', 5),
            ('enrollment_modes.audit.count_change_7_days', 1),
            ...
            ('enrollment_modes.credit.count', 10),
            ...
        ]

        This function is used in this TestCase to help convert the expected JSON response into a CSV response.
        """
        nested_key_val_pairs = []
        for key, val in nested_dict.items():
            if isinstance(val, dict):
                nested_key_val_pairs.extend(self.collapse_nested_dict(val, dot_separated_key + [key]))
            else:
                nested_key_val_pairs.append(('.'.join(dot_separated_key + [key]), val))
        return nested_key_val_pairs

    def expected_summary(self, course_id, modes=None, availability='Current', output_format='json'):
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
            'availability': availability,
            'enrollment_modes': {},
            'count': count_factor * num_modes,
            'cumulative_count': cumulative_count_factor * num_modes,
            'count_change_7_days': count_change_factor * num_modes,
            'created': self.now.strftime(settings.DATETIME_FORMAT),
        }
        summary['enrollment_modes'].update({
            mode: {
                'count': count_factor,
                'cumulative_count': cumulative_count_factor,
                'count_change_7_days': count_change_factor,
            } for mode in modes
        })
        summary['enrollment_modes'].update({
            mode: {
                'count': 0,
                'cumulative_count': 0,
                'count_change_7_days': 0,
            } for mode in set(enrollment_modes.ALL) - set(modes)
        })
        no_prof = summary['enrollment_modes'].pop(enrollment_modes.PROFESSIONAL_NO_ID)
        prof = summary['enrollment_modes'].get(enrollment_modes.PROFESSIONAL)
        prof.update({
            'count': prof['count'] + no_prof['count'],
            'cumulative_count': prof['cumulative_count'] + no_prof['cumulative_count'],
            'count_change_7_days': prof['count_change_7_days'] + no_prof['count_change_7_days'],
        })
        if output_format == 'csv':
            # If the desired output is CSV, convert the dict constructed above into a list of two-element lists where
            # the first element is the column header title and the second element is the value for the specified
            # course.
            summary_csv = []
            for key, val in summary.items():
                if isinstance(val, dict):
                    # Flatten nested dicts to a list of dot-separated keys and atomic values and add them to
                    # summary_csv
                    for nested_key, nested_val in self.collapse_nested_dict(val, [key]):
                        summary_csv.append([nested_key, nested_val])
                else:
                    summary_csv.append([key, val])
            # The CsvViewMixin response sorts the columns alphabetically by their titles, while summary_csv is made
            # from an unordered dict. Sort summary_csv by the titles so the columns will match in a string comparison.
            summary_csv = sorted(summary_csv, key=lambda x: x[0])
            # Convert the list of columns into a string: the expected CSV response
            return '\n'.join([','.join(str(col[i]) for col in summary_csv) for i in range(len(summary_csv[0]))])
        return summary

    def all_expected_summaries(self, modes=None, course_ids=None, availability='Current'):
        if course_ids is None:
            course_ids = CourseSamples.course_ids

        if modes is None:
            modes = enrollment_modes.ALL

        return [self.expected_summary(course_id, modes, availability) for course_id in course_ids]

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
        ['enrollment_mode', 'course_id'],
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

    def test_collapse_upcoming(self):
        self.generate_data(availability='Starting Soon')
        self.generate_data(course_ids=['foo/bar/baz'], availability='Upcoming')
        response = self.authenticated_get(self.path())
        self.assertEquals(response.status_code, 200)

        expected_summaries = self.all_expected_summaries(availability='Upcoming')
        expected_summaries.extend(self.all_expected_summaries(course_ids=['foo/bar/baz'],
                                                              availability='Upcoming'))

        self.assertItemsEqual(response.data, expected_summaries)

    def test_csv_download(self):
        self.generate_data(course_ids=['edX/DemoX/Demo_Course'])
        response = self.authenticated_get(self.path(), HTTP_ACCEPT='text/csv')

        expected_summary = self.expected_summary('edX/DemoX/Demo_Course', output_format='csv')
        # Strip off trailing new line from response and normalize remaining new lines to '\n'
        self.assertEqual(response.content[:-2].replace('\r\n', '\n'), expected_summary)
