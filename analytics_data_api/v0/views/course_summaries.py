from django.db.models import Q

from analytics_data_api.constants import enrollment_modes
from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.views import APIListView
from analytics_data_api.v0.views.utils import (
    split_query_argument,
    validate_course_id,
)


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

    def get(self, request, *args, **kwargs):
        query_params = self.request.query_params
        programs = split_query_argument(query_params.get('programs'))
        if not programs:
            self.always_exclude = self.always_exclude + ['programs']
        response = super(CourseSummariesView, self).get(request, *args, **kwargs)
        return response

    def post(self, request, *args, **kwargs):
        # self.request.data is a QueryDict. For keys with singleton lists as values,
        # QueryDicts return the singleton element of the list instead of the list itself,
        # which is undesirable. So, we convert to a normal dict.
        request_data_dict = dict(self.request.data)
        programs = request_data_dict.get('programs')
        if not programs:
            self.always_exclude = self.always_exclude + ['programs']
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

    def base_field_dict(self, course_id):
        """Default summary with fields populated to default levels."""
        summary = super(CourseSummariesView, self).base_field_dict(course_id)
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
        field_dict = super(CourseSummariesView, self).update_field_dict_from_model(model,
                                                                                   base_field_dict=base_field_dict,
                                                                                   field_list=self.summary_meta_fields)
        field_dict['enrollment_modes'].update({
            model.enrollment_mode: {field: getattr(model, field) for field in self.count_fields}
        })

        # treat the most recent as the authoritative created date -- should be all the same
        field_dict['created'] = max(model.created, field_dict['created']) if field_dict['created'] else model.created

        # update totals for all counts
        field_dict.update({field: field_dict[field] + getattr(model, field) for field in self.count_fields})

        return field_dict

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

        if self.exclude == [] or (self.exclude and 'programs' not in self.exclude):
            # don't do expensive looping for programs if we are just going to throw it away
            field_dict = self.add_programs(field_dict)

        for field in self.exclude:
            for mode in field_dict['enrollment_modes']:
                _ = field_dict['enrollment_modes'][mode].pop(field, None)

        return field_dict

    def add_programs(self, field_dict):
        """Query for programs attached to a course and include them (just the IDs) in the course summary dict"""
        field_dict['programs'] = []
        queryset = self.programs_model.objects.filter(course_id=field_dict['course_id'])
        for program in queryset:
            program = self.programs_serializer_class(program.__dict__)
            field_dict['programs'].append(program.data['program_id'])
        return field_dict

    def get_query(self):
        return reduce(lambda q, item_id: q | Q(course_id=item_id), self.ids, Q())
