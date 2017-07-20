from django.db.models import Q
from django.http import Http404
from django.utils import timezone

from django.core.paginator import InvalidPage

from rest_framework.pagination import PageNumberPagination

from analytics_data_api.constants import enrollment_modes
from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.views import APIListView
from analytics_data_api.v0.views.utils import (
    raise_404_if_none,
    split_query_argument_as_set,
    validate_course_id,
)


def _positive_int(integer_string, strict=False, cutoff=None):
    """
    Cast a string to a strictly positive integer.
    """
    ret = int(integer_string)
    if ret < 0 or (ret == 0 and strict):
        raise ValueError()
    if cutoff:
        return min(ret, cutoff)
    return ret


class CourseSummariesPaginator(PageNumberPagination):
    page_size_query_param = 'page_size'
    page_size = 100
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate a queryset if required, either returning a
        page object, or `None` if pagination is not configured for this view.
        """
        if request.method == 'GET':
            return super(CourseSummariesPaginator, self).paginate_queryset(
                queryset,
                request,
                view=view
            )

        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = request.data.get(self.page_query_param, 1)
        if page_number in self.last_page_strings:
            page_number = paginator.num_pages

        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=exc.message
            )
            raise Http404(msg)

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request
        return list(self.page)

    def get_page_size(self, request):
        if request.method == 'GET':
            return super(CourseSummariesPaginator, self).get_page_size(request)

        if self.page_size_query_param and self.page_size_query_param in request.data:
            try:
                return _positive_int(
                    request.data.get(self.page_size_query_param),
                    strict=True,
                    cutoff=self.max_page_size
                )
            except (KeyError, ValueError):
                pass
        return self.page_size


class CourseSummariesView(APIListView):
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
    enable_caching = True

    serializer_class = serializers.CourseMetaSummaryEnrollmentSerializer
    pagination_class = CourseSummariesPaginator
    model = models.CourseMetaSummaryEnrollment
    model_id_field = 'course_id'
    ids_param = 'course_ids'
    programs_model = models.CourseProgramMetadata
    count_fields = ('count', 'cumulative_count', 'count_change_7_days',
                    'passing_users')  # are initialized to 0 by default
    summary_meta_fields = ['catalog_course_title', 'catalog_course', 'start_time', 'end_time',
                           'pacing_type', 'availability']  # fields to extract from summary model
    sort_key_fields = set(count_fields) | set(summary_meta_fields) | set(['verified_enrollment'])

    def get(self, request, *args, **kwargs):
        params = request.query_params
        self.availability = split_query_argument_as_set(params.get('availability'))
        self.pacing_type = split_query_argument_as_set(params.get('pacing_type'))
        self.program_ids = split_query_argument_as_set(params.get('program_ids'))
        self.text_search = params.get('text_search')
        self.sort_key = params.get('sortKey')
        self.order = params.get('order')
        return super(CourseSummariesView, self).get(request, *args, **kwargs)
        return response

    def post(self, request, *args, **kwargs):
        self.availability = set(request.data.getlist('availability'))
        self.pacing_type = set(request.data.getlist('pacing_type'))
        self.program_ids = set(request.data.getlist('program_ids'))
        self.text_search = request.data.get('text_search')
        self.sort_key = request.data.get('sortKey')
        self.order = request.data.get('order')
        return super(CourseSummariesView, self).post(request, *args, **kwargs)

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
        summary['programs'] = set()
        return summary

    @classmethod
    def update_field_dict_from_model(cls, model, base_field_dict=None, field_list=None):
        super(CourseSummariesView, cls).update_field_dict_from_model(
            model,
            base_field_dict=base_field_dict,
            field_list=cls.summary_meta_fields,
        )
        field_dict = base_field_dict
        field_dict['enrollment_modes'].update({
            model.enrollment_mode: {field: getattr(model, field) for field in cls.count_fields}
        })

        # treat the most recent as the authoritative created date -- should be all the same
        field_dict['created'] = max(model.created, field_dict['created']) if field_dict['created'] else model.created

        # update totals for all counts
        field_dict.update({field: field_dict[field] + getattr(model, field) for field in cls.count_fields})

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
        for field in exclude:
            for mode in field_dict['enrollment_modes']:
                _ = field_dict['enrollment_modes'][mode].pop(field, None)

    from django.core.cache import caches
    cache = caches['summaries']
    cache_prefix = 'summary/'
    cache_flag = 'summaries-loaded-v9'
    cache_list_key = 'summaries-id-list'

    @classmethod
    def get_full_dataset(cls):
        queryset = cls.model.objects.all()
        summaries = cls.group_by_id_dict(queryset)
        course_programs = cls.programs_model.objects.all()
        for course_program in course_programs:
            summary = summaries.get(course_program.course_id)
            if not summary:
                continue
            summary['programs'].add(
                course_program.program_id
            )
        return summaries

    def _cache_valid(self):
        return bool(self.cache.get(self.cache_flag))

    def _prepare_cache(self):
        if not self._cache_valid():
            summary_dict = self.get_full_dataset()
            prefixed_summary_dict = {
                self.cache_prefix + course_id: summary
                for course_id, summary in summary_dict.iteritems()
            }
            import pdb; pdb.set_trace()
            self.cache.set_many(prefixed_summary_dict, timeout=None)
            self.cache.set(self.cache_list_key, summary_dict.keys(), timeout=None)
            self.cache.set(self.cache_flag, True, timeout=None)

    @raise_404_if_none
    def get_queryset(self):
        if not self.enable_caching:
            return super(CourseSummariesView, self).get_queryset()
        self._prepare_cache()

        def filter_func(model_dict):
            if self.availability and model_dict.get('availability') not in self.availability:
                return False
            if self.pacing_type and model_dict.get('pacing_type') not in self.pacing_type:
                return False
            if self.program_ids and not (model_dict.get('programs') | self.program_ids):
                return False
            if self.text_search:
                lower_search = self.text_search.lower()
                match = (
                    lower_search in (model_dict.get('course_id') or '').lower() or
                    lower_search in (model_dict.get('catalog_course_title') or '').lower()
                )
                if not match:
                    return False

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

        # Load from cache
        ids_to_load = self.ids or self.cache.get(self.cache_list_key)
        prefixed_ids = [self.cache_prefix + course_id for course_id in ids_to_load]
        model_dicts = self.cache.get_many(prefixed_ids).values()

        # Fitler
        model_dicts = [
            model_dict
            for model_dict in model_dicts
            if filter_func(model_dict)
        ]

        # Sort
        if self.sort_key in self.sort_key_fields:
            model_dicts = sorted(model_dicts, key=sorting_func)
            if self.order == 'desc':
                model_dicts.reverse()

        # Prepare for response
        for model_dict in model_dicts:
            self._do_excludes(model_dict, self.exclude)
        return model_dicts
