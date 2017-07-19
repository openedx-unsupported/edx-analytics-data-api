from collections import namedtuple

from django.db.models import Q
from django.http import Http404
from django.utils import timezone

from analytics_data_api.constants import enrollment_modes
from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.views import PaginatedAPIListView
from analytics_data_api.v0.views.utils import (
    raise_404_if_none,
    split_query_argument,
    validate_course_id,
)


class CourseSummariesView(PaginatedAPIListView):
    """
    Returns summary information for courses.

    **Example Requests**

        GET /api/v0/course_summaries/?course_ids={course_id_1},{course_id_2}

        POST /api/v0/course_summaries/
        {
            "course_ids": [
                "{course_id_1}",
                "{course_id_2}",
                ...
                "{course_id_200}"
            ]
        }

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

        Results can be filed to the course IDs specified or limited to the fields.

        For GET requests, these parameters are passed in the query string.
        For POST requests, these parameters are passed as a JSON dict in the request body.

        course_ids -- The comma-separated course identifiers for which summaries are requested.
            For example, 'edX/DemoX/Demo_Course,course-v1:edX+DemoX+Demo_2016'.  Default is to
            return all courses.
        fields -- The comma-separated fields to return in the response.
            For example, 'course_id,created'.  Default is to return all fields.
        exclude -- The comma-separated fields to exclude in the response.
            For example, 'course_id,created'.  Default is to exclude the programs array.
        programs -- If included in the query parameters, will find each courses' program IDs
            and include them in the response.

    **Notes**

        * GET is usable when the number of course IDs is relatively low
        * POST is required when the number of course IDs would cause the URL to be too long.
        * POST functions the same as GET for this endpoint. It does not modify any state.
    """
    default_page_size = 100
    max_page_size = 100
    enable_caching = True

    serializer_class = serializers.CourseMetaSummaryEnrollmentSerializer
    programs_serializer_class = serializers.CourseProgramMetadataSerializer
    model = models.CourseMetaSummaryEnrollment
    model_id_field = 'course_id'
    ids_param = 'course_ids'
    programs_model = models.CourseProgramMetadata
    count_fields = ('count', 'cumulative_count', 'count_change_7_days',
                    'passing_users')  # are initialized to 0 by default
    summary_meta_fields = ['catalog_course_title', 'catalog_course', 'start_time', 'end_time',
                           'pacing_type', 'availability']  # fields to extract from summary model
    sort_key_fields = set(count_fields) | set(summary_meta_fields) | set(['verified_enrollment'])

    @staticmethod
    def _get_string(data_dict, key, possible_values, is_from_querystring=False):
        raw_value = data_dict.get(key)
        if raw_value is None:
            return None
        elif is_from_querystring:
            value = raw_value
        elif raw_value == []:
            return None
        else:
            value = raw_value[0]
        if possible_values and value not in possible_values:
            raise Http404()  # @@ TODO what should this error be
        return value

    @staticmethod
    def _get_set(data_dict, key, is_from_querystring=False):
        raw_value = data_dict.get(key)
        if raw_value is None:
            return None
        elif is_from_querystring:
            return set(split_query_argument(raw_value))
        else:
            return set(raw_value)

    def get(self, request, *args, **kwargs):
        query_params = request.query_params
        self.availability = self._get_set(query_params, 'availability', True)
        self.pacing_type = self._get_set(query_params, 'pacing_type', True)
        self.program_ids = self._get_set(query_params, 'program_ids', True)
        self.text_search = self._get_string(query_params, 'text_search', None, True)
        self.sort_key = self._get_string(query_params, 'sortKey', self.sort_key_fields, True)
        self.order = self._get_string(query_params, 'order', set(['asc', 'desc']), True)
        response = super(CourseSummariesView, self).get(request, *args, **kwargs)
        return response

    def post(self, request, *args, **kwargs):
        # self.request.data is a QueryDict. For keys with singleton lists as values,
        # QueryDicts return the singleton element of the list instead of the list itself,
        # which is undesirable. So, we convert to a normal dict.
        request_data_dict = dict(request.data)
        programs = request_data_dict.get('programs')
        if not programs:
            self.always_exclude = self.always_exclude + ['programs']
        self.availability = self._get_set(request_data_dict, 'availability')
        self.pacing_type = self._get_set(request_data_dict, 'pacing_type')
        self.program_ids = self._get_set(request_data_dict, 'program_ids')
        self.text_search = self._get_string(request_data_dict, 'text_search', None)
        self.sort_key = self._get_string(request_data_dict, 'sortKey', self.sort_key_fields)
        self.order = self._get_string(request_data_dict, 'order', set(['asc', 'desc']))
        response = super(CourseSummariesView, self).post(request, *args, **kwargs)
        return response

    def verify_ids(self):
        """
        Raise an exception if any of the course IDs set as self.ids are invalid.
        Overrides APIListView.verify_ids.
        """
        if self.ids is not None:
            for item_id in self.ids:
                validate_course_id(item_id)

    @classmethod
    def base_field_dict(cls, course_id):
        """Default summary with fields populated to default levels."""
        summary = super(CourseSummariesView, cls).base_field_dict(course_id)
        summary.update({
            'created': None,
            'enrollment_modes': {},
        })
        summary.update({field: 0 for field in cls.count_fields})
        summary['enrollment_modes'].update({
            mode: {
                count_field: 0 for count_field in cls.count_fields
            } for mode in enrollment_modes.ALL
        })
        return summary

    @classmethod
    def update_field_dict_from_model(cls, model, base_field_dict=None, field_list=None):
        field_dict = super(CourseSummariesView, cls).update_field_dict_from_model(model,
                                                                                   base_field_dict=base_field_dict,
                                                                                   field_list=cls.summary_meta_fields)
        field_dict['enrollment_modes'].update({
            model.enrollment_mode: {field: getattr(model, field) for field in cls.count_fields}
        })

        # treat the most recent as the authoritative created date -- should be all the same
        field_dict['created'] = max(model.created, field_dict['created']) if field_dict['created'] else model.created

        # update totals for all counts
        field_dict.update({field: field_dict[field] + getattr(model, field) for field in cls.count_fields})

        return field_dict

    @classmethod
    def postprocess_field_dict(cls, field_dict, exclude):
        # Merge professional with non verified professional
        modes = field_dict['enrollment_modes']
        prof_no_id_mode = modes.pop(enrollment_modes.PROFESSIONAL_NO_ID, {})
        prof_mode = modes[enrollment_modes.PROFESSIONAL]
        for count_key in cls.count_fields:
            prof_mode[count_key] = prof_mode.get(count_key, 0) + prof_no_id_mode.pop(count_key, 0)

        # AN-8236 replace "Starting Soon" to "Upcoming" availability to collapse the two into one value
        if field_dict['availability'] == 'Starting Soon':
            field_dict['availability'] = 'Upcoming'

        # Add in verified_enrollment
        verified = modes.get('verified')
        field_dict['verified_enrollment'] = verified.get('count', 0) if verified else 0

        return field_dict

    @classmethod
    def _do_excludes(cls, field_dict, exclude):
        if exclude == [] or (exclude and 'programs' not in exclude):
            # don't do expensive looping for programs if we are just going to throw it away
            field_dict = cls.add_programs(field_dict)

        for field in exclude:
            for mode in field_dict['enrollment_modes']:
                _ = field_dict['enrollment_modes'][mode].pop(field, None)

    @classmethod
    def add_programs(cls, field_dict):
        """Query for programs attached to a course and include them (just the IDs) in the course summary dict"""
        field_dict['programs'] = []
        queryset = cls.programs_model.objects.filter(course_id=field_dict['course_id'])
        for program in queryset:
            program = cls.programs_serializer_class(program.__dict__)
            field_dict['programs'].append(program.data['program_id'])
        return field_dict

    from django.core.cache import caches
    cache = caches['summaries']
    cache_prefix = 'summary/'
    cache_flag = 'summaries-loaded-v5'

    def _cache_valid(self):
        return bool(self.cache.get(self.cache_flag))

    def _prepare_cache(self):
        if not self._cache_valid():
            summary_dict = self.get_full_dataset()
            prefixed_summary_dict = {
                self.cache_prefix + course_id: summary
                for course_id, summary in summary_dict.iteritems()
            }
            self.cache.set_many(prefixed_summary_dict, timeout=None)
            self.cache.set(self.cache_flag, True)

    @raise_404_if_none
    def get_queryset(self):
        if not (self.enable_caching and self.ids):
            return super(CourseSummariesView, self).get_queryset()
        self._prepare_cache()

        def filter_func(model_dict):
            if self.availability and model_dicts['availability'] not in self.availability:
                return False
            if self.pacing_type and model_dicts['pacing_type'] not in self.pacing_type:
                return False
            if self.program_ids and not (model_dicts['program_ids'] | self.program_ids):
                return False
            if self.text_search and False:  # @@TODO: text search
                return Falses
            return True

        max_datetime = timezone.make_aware(timezone.datetime.max, timezone.get_default_timezone())
        sorting_defaults = {
            'start_time': max_datetime,
            'end_time': max_datetime,
            'catalog_course_title': ''
        }

        def sorting_func(model_dict):
            sort_value = model_dict.get(self.sort_key)
            return sorting_defaults[self.sort_key] if sort_value is None else sort_value

        prefixed_ids = [self.cache_prefix + course_id for course_id in self.ids]
        model_dicts = self.cache.get_many(prefixed_ids).values()
        model_dicts = [
            model_dict
            for model_dict in model_dicts
            if filter_func(model_dict)
        ]
        if self.sort_key:
            model_dicts = sorted(model_dicts, key=sorting_func)
            if self.order == 'desc':
                model_dicts.reverse()
        for model_dict in model_dicts:
            self._do_excludes(model_dict, self.exclude)
        start = 0 if self.page is None else (self.page - 1) * self.page_size
        stop = 1000000 if self.page is None else start + self.page_size
        return model_dicts[start:stop]
