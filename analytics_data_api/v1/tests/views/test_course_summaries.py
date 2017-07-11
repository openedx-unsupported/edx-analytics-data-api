import datetime

import ddt
from django_dynamic_fixture import G
import pytz

from django.conf import settings

from analytics_data_api.constants import enrollment_modes
from analytics_data_api.v1 import models, serializers
from analytics_data_api.v1.tests.views import (
    CourseSamples,
    PaginatedAPIListViewTestMixin,
    PostableAPIListViewTestMixin,
    VerifyCourseIdMixin,
)
from analyticsdataserver.tests import TestCaseWithAuthentication


@ddt.ddt
class CourseSummariesViewTests(
        VerifyCourseIdMixin,
        PaginatedAPIListViewTestMixin,
        PostableAPIListViewTestMixin,
        TestCaseWithAuthentication,
):
    model = models.CourseMetaSummaryEnrollment
    model_id = 'course_id'
    ids_param = 'course_ids'
    serializer = serializers.CourseMetaSummaryEnrollmentSerializer
    expected_summaries = []
    list_name = 'course_summaries'
    default_ids = CourseSamples.course_ids
    always_exclude = ['created']
    test_post_method = True

    def setUp(self):
        super(CourseSummariesViewTests, self).setUp()
        self.now = datetime.datetime.utcnow()
        self.maxDiff = None

    def tearDown(self):
        self.model.objects.all().delete()

    def create_model(self, model_id, **kwargs):
        model_kwargs = {
            'course_id': model_id,
            'catalog_course_title': 'Title',
            'catalog_course': 'Catalog',
            'start_time': datetime.datetime(2016, 10, 11, tzinfo=pytz.utc),
            'end_time': datetime.datetime(2016, 12, 18, tzinfo=pytz.utc),
            'pacing_type': 'instructor',
            'availability': None,
            'count': 5,
            'cumulative_count': 10,
            'count_change_7_days': 1,
            'passing_users': 1,
            'create': self.now
        }
        model_kwargs.update(kwargs)
        for mode in kwargs['modes']:
            G(self.model, enrollment_mode=mode, **model_kwargs)
        # Create a link from this course to programs
        program_ids = kwargs['programs'] if 'programs' in kwargs else [CourseSamples.program_ids[0]]
        for i, program_id in enumerate(program_ids or []):
            G(
                models.CourseProgramMetadata,
                course_id=model_id,
                program_id=program_id,
                program_type='Demo',
                program_title=('Test #' + str(i)),
            )

    def generate_data(self, ids=None, modes=None, availability='Current', **kwargs):
        """Generate course summary data"""
        if modes is None:
            modes = enrollment_modes.ALL

        super(CourseSummariesViewTests, self).generate_data(ids=ids, modes=modes, availability=availability, **kwargs)

    def expected_result(self, item_id, modes=None, availability='Current'):  # pylint: disable=arguments-differ
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
            ('verified_enrollment', count_factor if 'verified' in modes else 0),
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
        summary['programs'] = [CourseSamples.program_ids[0]]
        return summary

    def all_expected_results(self, ids=None, modes=None, availability='Current'):  # pylint: disable=arguments-differ
        if modes is None:
            modes = enrollment_modes.ALL

        return super(CourseSummariesViewTests, self).all_expected_results(
            ids=ids,
            modes=modes,
            availability=availability
        )

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
        results = self.validated_request(200, exclude=self.always_exclude)
        self.assertItemsEqual(results, self.all_expected_results(modes=modes))

    @ddt.data(
        ['malformed-course-id'],
        [CourseSamples.course_ids[0], 'malformed-course-id'],
    )
    def test_bad_course_id(self, course_ids):
        data = {self.ids_param: course_ids}
        response = self.authenticated_get(self.path(data))
        self.verify_bad_course_id(response)
        response = self.authenticated_post(self.path(), data=data)
        self.verify_bad_course_id(response)

    def test_collapse_upcoming(self):
        self.generate_data(availability='Starting Soon')
        self.generate_data(ids=['foo/bar/baz'], availability='Upcoming')
        actual_results = self.validated_request(200, exclude=self.always_exclude)

        expected_results = (
            self.all_expected_results(availability='Upcoming') +
            self.all_expected_results(ids=['foo/bar/baz'], availability='Upcoming')
        )
        self.assertItemsEqual(actual_results, expected_results)

    def test_programs(self):
        self.generate_data()
        actual_results = self.validated_request(200, exclude=self.always_exclude[:1])
        expected_results = self.all_expected_results()
        self.assertItemsEqual(actual_results, expected_results)

    @ddt.data(['passing_users', 'count_change_7_days'], ['passing_users'])
    def test_exclude(self, fields):
        self.generate_data()
        results = self.validated_request(200, exclude=fields)
        for field in fields:
            self.assertEquals(str(results).count(field), 0)

    @ddt.data(
        {
            # Case 1 -- We can:
            #    * Sort numeric values, including negative ones
            #    * Specify an ascending sort order
            #    * Specify a page size AND a page
            'order_by': ('count_change_7_days', 'count_change_7_days'),
            'values': [10, 5, 15, -5],
            'sort_order': 'asc',
            'page': 1,
            'page_size': 2,
            'expected_order': [3, 1],
        },
        {
            # Case 2 -- We can:
            #    * Sort dates, including None (which should act as min datetime)
            #    * Specify a descending sort order
            #    * NOT specify a page size, and get the max size (up to 100)
            #    * Specify a page
            'order_by': ('start_time', 'start_date'),
            'values': [
                datetime.datetime(2016, 1, 1, tzinfo=pytz.utc),
                None,
                datetime.datetime(2018, 1, 1, tzinfo=pytz.utc),
                datetime.datetime(2017, 1, 1, tzinfo=pytz.utc),
            ],
            'sort_order': 'desc',
            'page': 1,
            'expected_order': [2, 3, 0, 1],
        },
        {
            # Case 3 -- We can:
            #    * Sort strings, including None/empty (which should act as maximum string)
            #    * NOT specify an order, defaulting to ascending
            #    * Specify a page size AND a page
            'order_by': ('catalog_course_title', 'catalog_course_title'),
            'values': ['Zoology 101', '', None, 'Anthropology 101'],
            'page_size': 1,
            'page': 2,
            'expected_order': [0],
        },
        {
            # Case 4 -- We can:
            #    * Sort ints, including zero
            #    * NOT specify an order, defaulting to ascending
            #    * Specify a page size larger than the count, and get all results
            #    * Specify a page size
            'order_by': ('passing_users', 'passing_users'),
            'values': [0, 1, 2, 3],
            'page_size': 50,
            'page': 1,
            'expected_order': [0, 1, 2, 3],
        },
        {
            # Case 5 -- We get a 400 if we pass in an invalid order_by
            'order_by': ('count', 'BAD_ORDER_BY'),
            'values': [0, 0, 0, 0],
            'expected_status_code': 400,
        },
        {
            # Case 6 -- We get a 400 if we pass in an invalid sort_order
            'order_by': ('count', 'count'),
            'values': [0, 0, 0, 0],
            'sort_order': 'BAD_SORT_ORDER',
            'expected_status_code': 400,
        },
        {
            # Case 7 -- We get a 200 if we pass in a negative page size
            'page_size': -1,
            'page': 1,
            'expected_status_code': 200,
        },
        {
            # Case 8 -- We get a 200 if we pass in a zero page size
            'page_size': 0,
            'page': 1,
            'expected_status_code': 200,
        },
        {
            # Case 9 -- We get a 200 if we pass in a too-large page size
            'page_size': 200,
            'page': 1,
            'expected_status_code': 200,
        },
        {
            # Case 10 -- We get a 200 if we pass in a non-int page size
            'page_size': 'BAD_PAGE_SIZE',
            'page': 1,
            'expected_status_code': 200,
        },
        {
            # Case 11 -- We get a 404 if we pass in an invalid page
            'page_size': 50,
            'page': 2,
            'expected_status_code': 404,
        },
        {
            # Case 12 -- We get a 404 if we pass in a non-int page
            'page': 'BAD_PAGE',
            'expected_status_code': 404,
        },
        {
            # Case 12 -- We get a 404 if we don't pass in a page
            'expected_status_code': 404,
        },
    )
    @ddt.unpack
    def test_sorting_and_pagination(
            self,
            order_by=(None, None),
            values=None,
            sort_order=None,
            page=None,
            page_size=None,
            expected_status_code=200,
            expected_order=None,
    ):
        # Create models in order with course IDs and given values
        for course_id, value in zip(CourseSamples.four_course_ids, values or [None] * 4):
            self.generate_data(
                ids=[course_id],
                **({order_by[0]: value} if order_by[0] else {})
            )

        # Perform the request, checking the response code
        data = self.validated_request(
            expected_status_code,
            order_by=[order_by[1]],
            sort_order=[sort_order],
            fields=['course_id'],
            page_size=[str(page_size)],
            page=[str(page)],
            extract_results=False,
        )
        if expected_status_code >= 300:
            return

        # Make sure the total count is 4
        self.assertEqual(data['count'], 4)

        # Make sure the page size is right
        try:
            expected_page_size = int(page_size)
        except (ValueError, TypeError):
            expected_page_size = 4
        if expected_page_size < 1 or expected_page_size > 4:
            expected_page_size = 4
        actual_page_size = len(data['results'])
        self.assertEqual(expected_page_size, actual_page_size)

        # If we are checking order, make sure it's right
        if expected_order:
            actual_order = [
                CourseSamples.four_course_ids.index(result['course_id'])
                for result in data['results']
            ]
            self.assertEqual(actual_order, expected_order)

    filter_test_dicts = [
        {
            'ids': ['course-v1:a+b+c'],
            'catalog_course_title': 'New Course ABC',
            'availability': 'Upcoming',
            'pacing_type': 'self_paced',
            'programs': ['program-1', 'program-2'],
        },
        {
            'ids': ['b/c/d'],
            'catalog_course_title': 'Old Course BCD',
            'availability': 'unknown',
            'pacing_type': 'instructor_paced',
            'programs': ['program-1'],
        },
        {
            'ids': ['ccx-v1:c+d+e'],
            'catalog_course_title': 'CCX Course CDE',
            'availability': None,
            'pacing_type': None,
            'programs': [],
        },
    ]

    @ddt.data(
        {
            # Case 1: If no search/filters, all are returned
            'expected_indices': frozenset([0, 1, 2]),
        },
        {
            # Case 2: Can search in course IDs w/ special symbols
            'text_search': '+',
            'expected_indices': frozenset([0, 2]),
        },
        {
            # Case 3: Can search in course titles, case insensitive
            'text_search': 'cOURSE',
            'expected_indices': frozenset([0, 1, 2]),
        },
        {
            # Case 4: No search results
            'text_search': 'XYZ',
            'expected_indices': frozenset(),
        },
        {
            # Case 5: Can filter by availability, and None availabilities
            # are returned by 'unknown' filter
            'availability': ['unknown'],
            'expected_indices': frozenset([1, 2]),
        },
        {
            # Case 6: Can filter by multiple availabilities
            'availability': ['Upcoming', 'Current'],
            'expected_indices': frozenset([0]),
        },
        {
            # Case 7: Can filter by a single pacing type
            'pacing_type': ['self_paced'],
            'expected_indices': frozenset([0]),
        },
        {
            # Case 8: Can filter by a multiple pacing types
            'pacing_type': ['self_paced', 'instructor_paced'],
            'expected_indices': frozenset([0, 1]),
        },
        {
            # Case 9: Can filter by program
            'program_ids': ['program-1'],
            'expected_indices': frozenset([0, 1]),
        },
        {
            # Case 10: Can filter by multiple programs, even if one doesn't exist
            'program_ids': ['program-2', 'program-3'],
            'expected_indices': frozenset([0]),
        },
        {
            # Case 11: Bad filter value returns 400
            'pacing_type': ['BAD_PACING_TYPE'],
            'expected_status_code': 400,
        },
    )
    @ddt.unpack
    def test_filtering_and_searching(
            self,
            expected_indices=None,
            text_search=None,
            expected_status_code=200,
            **filters
    ):
        for test_dict in self.filter_test_dicts:
            self.generate_data(**test_dict)
        results = self.validated_request(expected_status_code, text_search=[text_search], **filters)
        if expected_status_code >= 300:
            return
        actual_ids = frozenset(result['course_id'] for result in results)
        expected_ids = set()
        for index in expected_indices:
            expected_ids.add(self.filter_test_dicts[index]['ids'][0])
        self.assertEqual(actual_ids, expected_ids)
