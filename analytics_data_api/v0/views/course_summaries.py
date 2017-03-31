from django.db.models import Q

from analytics_data_api.constants import enrollment_modes
from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.views import APIListView
from analytics_data_api.v0.views.utils import (
    validate_course_id,
)


class CourseSummariesView(APIListView):
    """
    Returns summary information for courses.

    **Example Request**

        GET /api/v0/course_summaries/?ids={course_id},{course_id}

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

        course_ids -- The comma-separated course identifiers for which summaries are requested.
            For example, 'edX/DemoX/Demo_Course,course-v1:edX+DemoX+Demo_2016'.  Default is to
            return all courses.
        fields -- The comma-separated fields to return in the response.
            For example, 'course_id,created'.  Default is to return all fields.
        exclude -- The comma-separated fields to exclude in the response.
            For example, 'course_id,created'.  Default is to exclude the programs array.
    """
    exclude = ('programs',)
    serializer_class = serializers.CourseMetaSummaryEnrollmentSerializer
    programs_serializer_class = serializers.CourseProgramMetadataSerializer
    model = models.CourseMetaSummaryEnrollment
    model_id = 'course_id'
    programs_model = models.CourseProgramMetadata
    count_fields = ('count', 'cumulative_count', 'count_change_7_days')  # are initialized to 0 by default
    summary_meta_fields = ['catalog_course_title', 'catalog_course', 'start_time', 'end_time',
                           'pacing_type', 'availability']  # fields to extract from summary model

    def verify_ids(self):
        if self.ids is not None:
            for item_id in self.ids:
                validate_course_id(item_id)

    def default_result(self, item_id):
        """Default summary with fields populated to default levels."""
        summary = super(CourseSummariesView, self).default_result(item_id)
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

    def get_result_from_model(self, model, base_result=None, field_list=None):
        result = super(CourseSummariesView, self).get_result_from_model(model, base_result=base_result,
                                                                        field_list=self.summary_meta_fields)
        result['enrollment_modes'].update({
            model.enrollment_mode: {field: getattr(model, field) for field in self.count_fields}
        })

        # treat the most recent as the authoritative created date -- should be all the same
        result['created'] = max(model.created, result['created']) if result['created'] else model.created

        # update totals for all counts
        result.update({field: result[field] + getattr(model, field) for field in self.count_fields})

        return result

    def postprocess_result(self, result):
        # Merge professional with non verified professional
        modes = result['enrollment_modes']
        prof_no_id_mode = modes.pop(enrollment_modes.PROFESSIONAL_NO_ID, {})
        prof_mode = modes[enrollment_modes.PROFESSIONAL]
        for count_key in self.count_fields:
            prof_mode[count_key] = prof_mode.get(count_key, 0) + prof_no_id_mode.pop(count_key, 0)

        # AN-8236 replace "Starting Soon" to "Upcoming" availability to collapse the two into one value
        if result['availability'] == 'Starting Soon':
            result['availability'] = 'Upcoming'

        if self.exclude and 'programs' not in self.exclude:
            # don't do expensive looping for programs if we are just going to throw it away
            result = self.add_programs(result)

        return result

    def add_programs(self, result):
        """Query for programs attached to a course and include them (just the IDs) in the course summary dict"""
        result['programs'] = []
        queryset = self.programs_model.objects.filter(course_id=result['course_id'])
        for program in queryset:
            program = self.programs_serializer_class(program)
            result['programs'].append(program.data['program_id'])
        return result

    def get_query(self):
        return reduce(lambda q, item_id: q | Q(course_id=item_id), self.ids, Q())
