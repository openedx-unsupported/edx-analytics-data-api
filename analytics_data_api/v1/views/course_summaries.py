from django.utils import timezone

from rest_framework.generics import ListAPIView
from analytics_data_api.constants import enrollment_modes
from analytics_data_api.utils import join_dicts
from analytics_data_api.v1 import models, serializers
from analytics_data_api.v1.views.base import (
    AggregatedListAPIViewMixin,
    CachedListAPIViewMixin,
    DynamicFieldsAPIViewMixin,
    FilteredListAPIViewMixin,
    FilterPolicy,
    ModelListAPIViewMixin,
    PostAsGetAPIViewMixin,
    SearchedListAPIViewMixin,
    SortedListAPIViewMixin,
    SortPolicy,
)
from analytics_data_api.v1.views.pagination import PostAsGetPaginationBase
from analytics_data_api.v1.views.utils import validate_course_id


class CourseSummariesPagination(PostAsGetPaginationBase):
    page_size = 100
    max_page_size = None


class CourseSummariesView(
        CachedListAPIViewMixin,
        AggregatedListAPIViewMixin,
        ModelListAPIViewMixin,
        FilteredListAPIViewMixin,
        SearchedListAPIViewMixin,
        SortedListAPIViewMixin,
        DynamicFieldsAPIViewMixin,
        PostAsGetAPIViewMixin,
        ListAPIView,
):
    """
    Returns summary information for courses.

    **Example Requests**
        ```
        GET /api/v1/course_summaries/?course_ids={course_id_1},{course_id_2}
                                     &order_by=catalog_course_title
                                     &sort_order=desc
                                     &availability=Archived,Upcoming
                                     &program_ids={program_id_1},{program_id_2}
                                     &text_search=harvardx
                                     &page=3
                                     &page_size=50

        POST /api/v1/course_summaries/
        {
            "course_ids": [
                "{course_id_1}",
                "{course_id_2}",
                ...
                "{course_id_200}"
            ],
            "order_by": "catalog_course_title",
            "sort_order": "desc",
            "availability": ["Archived", "Upcoming"],
            "program_ids": ["{program_id_1}", "{program_id_2}"}],
            "text_search": "harvardx",
            "page": 3,
            "page_size": 50
        }
        ```

    **Response Values**

        Returns enrollment counts and other metadata for each course:

            * course_id: The ID of the course for which data is returned.
            * catalog_course_title: The name of the course.
            * catalog_course: Course identifier without run.
            * start_date: The date and time that the course begins
            * end_date: The date and time that the course ends
            * pacing_type: The type of pacing for this course
            * availability: Availability status of the course
            * count: The total count of currently enrolled learners across modes.
            * cumulative_count: The total cumulative total of all users ever enrolled across modes.
            * count_change_7_days: Total difference in enrollment counts over the past 7 days across modes.
            * enrollment_modes: For each enrollment mode, the count, cumulative_count, and count_change_7_days.
            * created: The date the counts were computed.
            * programs: List of program IDs that this course is a part of.

    **Parameters**

        Results can be filtered, sorted, and paginated. Also, specific fields can be
        included or excluded. All parameters are optional EXCEPT page.

        For GET requests:
            * Arguments are passed in the query string.
            * List values are passed in as comma-delimited strings.
        For POST requests:
            * Arguments are passed in as a JSON dict in the request body.
            * List values are passed as JSON arrays of strings.

        * order_by -- The column to sort by. One of the following:
            * catalog_course_title: The course title.
            * start_date: The course's start datetime.
            * end_date: The course's end datetime.
            * cumulative_count: Total number of enrollments.
            * count: Number of current enrollments.
            * count_change_7_days: Change in current enrollments in past week
            * verified_enrollment: Number of current verified enrollments.
            * passing_users: Number of users who are passing
            (Defaults to catalog_course_title)
        * sort_order -- Order of the sort. One of the following:
            * asc
            * desc
            (Defaults to asc)
        * course_ids -- List of IDs of courses to filter by.
            (Defaults to all courses)
        * availability -- List of availabilities to filter by. List containing
          one or more of the following:
            * Archived
            * Current
            * Upcoming
            * Unknown
            (Defaults to all availabilities)
        * program_ids -- List of IDs of programs to filter by.
            (Defaults to all programs)
        * text_search -- Sub-string to search for in course titles and IDs.
            (Defaults to no search filtering)
        * page (REQUIRED) -- Page number.
        * page_size -- Size of page. Must be in range [1, 100]
            (Defaults to 100)
        * fields -- Fields of course summaries to return in response. Mutually
          exclusive with `exclude` parameter.
            (Defaults to including all fields)
        * exclude -- Fields of course summaries to NOT return in response.
          Mutually exclusive with `fields` parameter.
            (Defaults to exluding no fields)

    **Notes**

        * GET is usable when the number of course IDs is relatively low.
        * POST is required when the number of course IDs would cause the URL to
          be too long.
        * POST functions semantically as GET for this endpoint. It does not
          modify any state.
    """
    _COUNT_FIELDS = frozenset([
        'count',
        'cumulative_count',
        'count_change_7_days',
        'passing_users',
    ])
    _TZ = timezone.get_default_timezone()
    _MIN_DATETIME = timezone.make_aware(timezone.datetime.min, _TZ)
    _MAX_DATETIME = timezone.make_aware(timezone.datetime.max, _TZ)

    # From IDsAPIViewMixin
    id_field = 'course_id'
    ids_param = id_field + 's'

    # From ListAPIView
    serializer_class = serializers.CourseMetaSummaryEnrollmentSerializer
    pagination_class = CourseSummariesPagination

    # From ModelListAPIViewMixin
    model_class = models.CourseMetaSummaryEnrollment

    # From AggregatedListAPIViewMixin
    basic_aggregate_fields = frozenset([
        'catalog_course_title',
        'catalog_course',
        'start_time',
        'end_time',
        'pacing_type',
        'availability'
    ])
    calculated_aggregate_fields = join_dicts(
        {
            'created': (max, 'created', None),
        },
        {
            count_field: (sum, count_field, 0)
            for count_field in _COUNT_FIELDS
        }
    )

    # From CachedListAPIViewMixin
    enable_caching = True
    cache_name = 'summaries'
    cache_root_prefix = 'course-summaries/'
    data_version = 1

    # From FilteredListAPIViewMixin
    filter_policies = {
        'availability': FilterPolicy(
            value_map={
                'Archived': frozenset(['Archived']),
                'Current': frozenset(['Current']),
                'Upcoming': frozenset(['Upcoming']),
                'unknown': frozenset(['unknown', None]),
            }
        ),
        'pacing_type': FilterPolicy(values=frozenset(['self_paced', 'instructor_paced'])),
        'program_ids': FilterPolicy(field='programs'),
    }

    # From SearchListAPIViewMixin
    search_param = 'text_search'
    search_fields = frozenset(['catalog_course_title', 'course_id'])

    # From SortedListAPIViewMixin
    sort_policies = join_dicts(
        {
            'catalog_course_title': SortPolicy(default='zzzzzz'),
            'start_date': SortPolicy(field='start_time', default=_MIN_DATETIME),
            'end_date': SortPolicy(field='end_time', default=_MIN_DATETIME),
        },
        {
            count_field: SortPolicy(default=0)
            for count_field in _COUNT_FIELDS | frozenset(['verified_enrollment'])
        }
    )

    @classmethod
    def aggregate(cls, raw_items):
        result = super(CourseSummariesView, cls).aggregate(raw_items)

        # Add in programs
        course_programs = models.CourseProgramMetadata.objects.all()
        for course_program in course_programs:
            result_item = result.get(course_program.course_id)
            if not result_item:
                continue
            if 'programs' not in result_item:
                result_item['programs'] = set()
            result_item['programs'].add(
                course_program.program_id
            )

        return result

    @classmethod
    def aggregate_item_group(cls, item_id, raw_item_group):
        result = super(CourseSummariesView, cls).aggregate_item_group(
            item_id,
            raw_item_group,
        )

        # Add in enrollment modes
        raw_items_by_enrollment_mode = {
            raw_item.enrollment_mode: raw_item
            for raw_item in raw_item_group
        }
        result['enrollment_modes'] = {
            enrollment_mode: {
                count_field: getattr(
                    raw_items_by_enrollment_mode.get(enrollment_mode),
                    count_field,
                    0,
                )
                for count_field in cls._COUNT_FIELDS
            }
            for enrollment_mode in enrollment_modes.ALL
        }

        # Merge non-verified-professional with professional
        modes = result['enrollment_modes']
        for count_field, prof_no_id_val in modes[enrollment_modes.PROFESSIONAL_NO_ID].iteritems():
            modes[enrollment_modes.PROFESSIONAL][count_field] = (
                (prof_no_id_val or 0) +
                modes[enrollment_modes.PROFESSIONAL].get(count_field, 0)
            )
        del modes[enrollment_modes.PROFESSIONAL_NO_ID]

        # AN-8236 replace "Starting Soon" to "Upcoming" availability to collapse
        # the two into one value
        if result['availability'] == 'Starting Soon':
            result['availability'] = 'Upcoming'

        # Add in verified_enrollment
        verified = result['enrollment_modes'].get(enrollment_modes.VERIFIED)
        result['verified_enrollment'] = verified.get('count', 0) if verified else 0

        return result

    @classmethod
    def source_data_timestamp(cls):
        all_models = cls.model_class.objects.all()
        return (
            all_models[0].created if all_models.count() > 0
            else cls._MIN_DATETIME
        )

    @classmethod
    def validate_id_formats(cls, ids):
        if not ids:
            return
        for course_id in ids:
            validate_course_id(course_id)

    def process_items(self, items):
        processed_items = super(CourseSummariesView, self).process_items(items)
        if self.fields_to_exclude:
            self._exclude_from_enrollment_modes(processed_items, self.fields_to_exclude)
        return processed_items

    @staticmethod
    def _exclude_from_enrollment_modes(items, to_exclude):
        for item in items.values():
            if 'enrollment_modes' not in item:
                continue
            item['enrollment_modes'] = {
                mode: {
                    count_field: count
                    for count_field, count in counts.iteritems()
                    if count_field not in to_exclude
                }
                for mode, counts in item['enrollment_modes'].iteritems()
            }
