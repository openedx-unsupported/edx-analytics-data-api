from datetime import datetime
from functools import reduce as functools_reduce
from itertools import groupby

from django.db.models import Q
from django.http import HttpResponseBadRequest

from analytics_data_api.constants import enrollment_modes
from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.views import APIListView
from analytics_data_api.v0.views.utils import split_query_argument, validate_course_id


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
            * recent_count_change: If a recent_date parameter was given, this will be the count change since that date
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
        recent_date -- A date in the past to compute enrollement count change relative to, format should be YYYY-MM-DD

    **Notes**

        * GET is usable when the number of course IDs is relatively low
        * POST is required when the number of course IDs would cause the URL to be too long.
        * POST functions the same as GET for this endpoint. It does not modify any state.
    """
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
    recent_date = None

    def get(self, request, *args, **kwargs):
        query_params = self.request.query_params
        programs = split_query_argument(query_params.get('programs'))
        if not programs:
            self.always_exclude = self.always_exclude + ['programs']

        recent = query_params.get('recent_date')
        try:
            self.verify_recent_date(recent)
        except ValueError as err:
            return HttpResponseBadRequest(content='Error in recent_date: {}\n'.format(str(err)))

        response = super().get(request, *args, **kwargs)
        return response

    def post(self, request, *args, **kwargs):
        # self.request.data is a QueryDict. For keys with singleton lists as values,
        # QueryDicts return the singleton element of the list instead of the list itself,
        # which is undesirable. So, we convert to a normal dict.
        request_data_dict = dict(self.request.data)
        programs = request_data_dict.get('programs')
        if not programs:
            self.always_exclude = self.always_exclude + ['programs']

        recent = request_data_dict.get('recent_date')
        try:
            if recent:
                self.verify_recent_date(recent[0])  # Post argument always comes in as a list
        except ValueError as err:
            return HttpResponseBadRequest(content='Error in recent_date: {}\n'.format(str(err)))

        response = super().post(request, *args, **kwargs)
        return response

    def verify_recent_date(self, recent):
        if not recent:
            return
        self.recent_date = datetime.strptime(recent, '%Y-%m-%d')
        if (datetime.now() - self.recent_date).days <= 0:
            raise ValueError(f'"{self.recent_date}" is not in the past')

    def verify_ids(self):
        """
        Raise an exception if any of the course IDs set as self.ids are invalid.
        Overrides APIListView.verify_ids.
        """
        if self.ids is not None:
            for item_id in self.ids:
                validate_course_id(item_id)

    def base_field_dict(self, item_id):
        """Default summary with fields populated to default levels."""
        summary = super().base_field_dict(item_id)
        summary.update({
            'created': None,
            'enrollment_modes': {},
        })
        summary.update({field: 0 for field in self.count_fields})
        summary['enrollment_modes'].update({
            mode: {
                count_field: 0 for count_field in self.count_fields
            } for mode in enrollment_modes.ALL
        })
        return summary

    def update_field_dict_from_model(self, model, base_field_dict=None, field_list=None):
        field_dict = super().update_field_dict_from_model(model, base_field_dict=base_field_dict,
                                                          field_list=self.summary_meta_fields)
        field_dict['enrollment_modes'].update({
            model.enrollment_mode: {field: getattr(model, field) for field in self.count_fields}
        })

        # treat the most recent as the authoritative created date -- should be all the same
        field_dict['created'] = max(model.created, field_dict['created']) if field_dict['created'] else model.created

        # update totals for all counts
        field_dict.update({field: field_dict[field] + getattr(model, field) for field in self.count_fields})

        return field_dict

    # override parent group by ID in order to do recent date stuff efficiently
    def group_by_id(self, queryset):
        """Return results aggregated by a distinct ID."""
        aggregate_field_dict = []

        fetch_recents = self.recent_date and 'recent_count_change' not in self.exclude
        if fetch_recents:
            recent_counts = models.CourseEnrollmentDaily.objects.filter(
                date=self.recent_date
            )
            # add in the same course_id filter used by the main query
            if self.ids:
                recent_counts = recent_counts.filter(self.get_query())
            recents = dict()
            for c in recent_counts:
                recents[c.course_id] = c.count

        fetch_programs = self.exclude == [] or (self.exclude and 'programs' not in self.exclude)
        if fetch_programs:
            # Use retrieve all course_program metadata query related to the courses
            course_program_metadata_queryset = self.programs_model.objects.all()
            if self.ids:
                course_program_metadata_queryset = course_program_metadata_queryset.filter(
                    course_id__in=self.ids
                )
            programs_metadata = dict()
            for program_item in course_program_metadata_queryset:
                programs_metadata.setdefault(program_item.course_id, []).append(
                    self.programs_serializer_class(program_item.__dict__).data['program_id']
                )

        for item_id, model_group in groupby(queryset, lambda x: (getattr(x, self.model_id_field))):
            field_dict = self.base_field_dict(item_id)

            for model in model_group:
                field_dict = self.update_field_dict_from_model(model, base_field_dict=field_dict)

            if fetch_recents:
                field_dict = self.add_recent_count_change(field_dict, recents)

            if fetch_programs:
                field_dict['programs'] = programs_metadata[item_id]

            field_dict = self.postprocess_field_dict(field_dict)
            aggregate_field_dict.append(field_dict)

        return aggregate_field_dict

    def postprocess_field_dict(self, field_dict):
        # Merge professional with non verified professional
        modes = field_dict['enrollment_modes']
        prof_no_id_mode = modes.pop(enrollment_modes.PROFESSIONAL_NO_ID, {})
        prof_mode = modes[enrollment_modes.PROFESSIONAL]
        for count_key in self.count_fields:
            prof_mode[count_key] = prof_mode.get(count_key, 0) + prof_no_id_mode.pop(count_key, 0)

        # AN-8236 replace "Starting Soon" to "Upcoming" availability to collapse the two into one value
        if field_dict['availability'] == 'Starting Soon':
            field_dict['availability'] = 'Upcoming'

        for field in self.exclude:
            for mode in field_dict['enrollment_modes']:
                _ = field_dict['enrollment_modes'][mode].pop(field, None)

        return field_dict

    def add_recent_count_change(self, field_dict, recents):
        # Pick the most recent daily count on-or-before the desired date
        # If there are no daily counts before the desired date, assume 0
        course_id = field_dict['course_id']
        if course_id in recents:
            recent_count = recents[course_id]
        else:
            recent_count = 0
        field_dict['recent_count_change'] = field_dict['count'] - recent_count
        return field_dict

    def get_query(self):
        return functools_reduce(lambda q, item_id: q | Q(course_id=item_id), self.ids, Q())
