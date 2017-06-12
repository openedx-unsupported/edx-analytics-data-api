import datetime

import ddt
from django_dynamic_fixture import G
import pytz

from django.conf import settings

from analytics_data_api.constants import enrollment_modes
from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.tests.views import CourseSamples, VerifyCourseIdMixin, APIListViewTestMixin
from analyticsdataserver.tests import TestCaseWithAuthentication


@ddt.ddt
class CourseSummariesViewTests(VerifyCourseIdMixin, TestCaseWithAuthentication, APIListViewTestMixin):
    model = models.CourseMetaSummaryEnrollment
    model_id = 'course_id'
    ids_param = 'course_ids'
    serializer = serializers.CourseMetaSummaryEnrollmentSerializer
    expected_summaries = []
    list_name = 'course_summaries'
    default_ids = CourseSamples.course_ids
    always_exclude = ['created', 'programs']
    test_post_method = True

    def setUp(self):
        super(CourseSummariesViewTests, self).setUp()
        self.now = datetime.datetime.utcnow()
        self.maxDiff = None

    def tearDown(self):
        self.model.objects.all().delete()

    def create_model(self, model_id, **kwargs):
        for mode in kwargs['modes']:
            G(self.model, course_id=model_id, catalog_course_title='Title', catalog_course='Catalog',
              start_time=datetime.datetime(2016, 10, 11, tzinfo=pytz.utc),
              end_time=datetime.datetime(2016, 12, 18, tzinfo=pytz.utc),
              pacing_type='instructor', availability=kwargs['availability'], enrollment_mode=mode,
              count=5, cumulative_count=10, count_change_7_days=1, passing_users=1, create=self.now,)
        if 'programs' in kwargs and kwargs['programs']:
            # Create a link from this course to a program
            G(models.CourseProgramMetadata, course_id=model_id, program_id=CourseSamples.program_ids[0],
              program_type='Demo', program_title='Test')

    def generate_data(self, ids=None, modes=None, availability='Current', **kwargs):
        """Generate course summary data"""
        if modes is None:
            modes = enrollment_modes.ALL

        super(CourseSummariesViewTests, self).generate_data(ids=ids, modes=modes, availability=availability, **kwargs)

    def expected_result(self, item_id, modes=None, availability='Current', programs=False):  # pylint: disable=arguments-differ
        """Expected summary information for a course and modes to populate with data."""
        summary = super(CourseSummariesViewTests, self).expected_result(item_id)

        if modes is None:
            modes = enrollment_modes.ALL

        num_modes = len(modes)
        count_factor = 5
        cumulative_count_factor = 10
        count_change_factor = 1
        summary.update([
            ('catalog_course_title', 'Title'),
            ('catalog_course', 'Catalog'),
            ('start_date', datetime.datetime(2016, 10, 11, tzinfo=pytz.utc).strftime(settings.DATETIME_FORMAT)),
            ('end_date', datetime.datetime(2016, 12, 18, tzinfo=pytz.utc).strftime(settings.DATETIME_FORMAT)),
            ('pacing_type', 'instructor'),
            ('availability', availability),
            ('count', count_factor * num_modes),
            ('cumulative_count', cumulative_count_factor * num_modes),
            ('count_change_7_days', count_change_factor * num_modes),
            ('passing_users', count_change_factor * num_modes),
            ('enrollment_modes', {}),
        ])
        summary['enrollment_modes'].update({
            mode: {
                'count': count_factor,
                'cumulative_count': cumulative_count_factor,
                'count_change_7_days': count_change_factor,
                'passing_users': count_change_factor,
            } for mode in modes
        })
        summary['enrollment_modes'].update({
            mode: {
                'count': 0,
                'cumulative_count': 0,
                'count_change_7_days': 0,
                'passing_users': 0,
            } for mode in set(enrollment_modes.ALL) - set(modes)
        })
        no_prof = summary['enrollment_modes'].pop(enrollment_modes.PROFESSIONAL_NO_ID)
        prof = summary['enrollment_modes'].get(enrollment_modes.PROFESSIONAL)
        prof.update({
            'count': prof['count'] + no_prof['count'],
            'cumulative_count': prof['cumulative_count'] + no_prof['cumulative_count'],
            'count_change_7_days': prof['count_change_7_days'] + no_prof['count_change_7_days'],
            'passing_users': prof['passing_users'] + no_prof['passing_users'],
        })
        if programs:
            summary['programs'] = [CourseSamples.program_ids[0]]
        return summary

    def all_expected_results(self, ids=None, modes=None, availability='Current', programs=False):  # pylint: disable=arguments-differ
        if modes is None:
            modes = enrollment_modes.ALL

        return super(CourseSummariesViewTests, self).all_expected_results(ids=ids, modes=modes,
                                                                          availability=availability,
                                                                          programs=programs)

    @ddt.data(
        None,
        CourseSamples.course_ids,
        ['not/real/course'].extend(CourseSamples.course_ids),
    )
    def test_all_courses(self, course_ids):
        self._test_all_items(course_ids)

    @ddt.data(*CourseSamples.course_ids)
    def test_one_course(self, course_id):
        self._test_one_item(course_id)

    @ddt.data(
        ['availability'],
        ['enrollment_mode', 'course_id'],
    )
    def test_fields(self, fields):
        self._test_fields(fields)

    @ddt.data(
        [enrollment_modes.VERIFIED],
        [enrollment_modes.HONOR, enrollment_modes.PROFESSIONAL],
    )
    def test_empty_modes(self, modes):
        self.generate_data(modes=modes)
        response = self.validated_request(exclude=self.always_exclude)
        self.assertEquals(response.status_code, 200)
        self.assertItemsEqual(response.data, self.all_expected_results(modes=modes))

    @ddt.data(
        ['malformed-course-id'],
        [CourseSamples.course_ids[0], 'malformed-course-id'],
    )
    def test_bad_course_id(self, course_ids):
        response = self.validated_request(ids=course_ids)
        self.verify_bad_course_id(response)

    def test_collapse_upcoming(self):
        self.generate_data(availability='Starting Soon')
        self.generate_data(ids=['foo/bar/baz'], availability='Upcoming')
        response = self.validated_request(exclude=self.always_exclude)
        self.assertEquals(response.status_code, 200)

        expected_summaries = self.all_expected_results(availability='Upcoming')
        expected_summaries.extend(self.all_expected_results(ids=['foo/bar/baz'],
                                                            availability='Upcoming'))

        self.assertItemsEqual(response.data, expected_summaries)

    def test_programs(self):
        self.generate_data(programs=True)
        response = self.validated_request(exclude=self.always_exclude[:1], programs=['True'])
        self.assertEquals(response.status_code, 200)
        self.assertItemsEqual(response.data, self.all_expected_results(programs=True))

    @ddt.data('passing_users', )
    def test_exclude(self, field):
        self.generate_data()
        response = self.validated_request(exclude=[field])
        self.assertEquals(response.status_code, 200)
        self.assertEquals(str(response.data).count(field), 0)
