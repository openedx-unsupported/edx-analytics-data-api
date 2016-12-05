from itertools import groupby

from django.db.models import Q

from rest_framework import generics

from analytics_data_api.constants import enrollment_modes
from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.views.utils import (
    raise_404_if_none,
    split_query_argument,
    validate_course_id,
)


class CourseSummariesView(generics.ListAPIView):
    """
    Returns summary information for courses.

    **Example Request**

        GET /api/v0/course_summaries/?course_ids={course_id},{course_id}

    **Response Values**

        Returns the count of each gender specified by users:

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

    **Parameters**

        Results can be filed to the course IDs specified or limited to the fields.

        course_ids -- The comma-separated course identifiers for which summaries are requested.
            For example, 'edX/DemoX/Demo_Course,course-v1:edX+DemoX+Demo_2016'.  Default is to
            return call courses.
        fields -- The comma-separated fields to return in the response.
            For example, 'course_id,created_mode'.  Default is to return all fields.

        fields -- Fields to include in response.  Default is all.
    """

    course_ids = None
    fields = None
    serializer_class = serializers.CourseMetaSummaryEnrollmentSerializer
    model = models.CourseMetaSummaryEnrollment

    def get_serializer(self, *args, **kwargs):
        kwargs.update({
            'context': self.get_serializer_context(),
            'fields': self.fields,
        })
        return self.get_serializer_class()(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        query_params = self.request.query_params
        self.fields = split_query_argument(query_params.get('fields'))
        self.course_ids = split_query_argument(query_params.get('course_ids'))
        if self.course_ids is not None:
            for course_id in self.course_ids:
                validate_course_id(course_id)

        return super(CourseSummariesView, self).get(request, *args, **kwargs)

    def default_summary(self, course_id, count_fields):
        """Default summary with fields populated to default levels."""
        summary = {
            'course_id': course_id,
            'created': None,
            'enrollment_modes': {},
        }
        summary.update({field: 0 for field in count_fields})
        summary['enrollment_modes'].update({
            mode: {
                count_field: 0 for count_field in count_fields
            } for mode in enrollment_modes.ALL
        })
        return summary

    def group_by_mode(self, queryset):
        """Return enrollment counts for nested in each mode and top-level enrollment counts."""
        formatted_data = []
        for course_id, summaries in groupby(queryset, lambda x: (x.course_id)):
            count_fields = ['count', 'count_change_7_days', 'cumulative_count']
            item = self.default_summary(course_id, count_fields)

            # aggregate the enrollment counts for each mode
            for summary in summaries:
                summary_meta_fields = ['catalog_course_title', 'catalog_course', 'start_time', 'end_time',
                                       'pacing_type', 'availability']
                item.update({field: getattr(summary, field) for field in summary_meta_fields})
                item['enrollment_modes'].update({
                    summary.enrollment_mode: {field: getattr(summary, field) for field in count_fields}
                })

                # treat the most recent as the authoritative created date -- should be all the same
                item['created'] = max(summary.created, item['created']) if item['created'] else summary.created

                # update totals for all counts
                item.update({field: item[field] + getattr(summary, field) for field in count_fields})

            # Merge professional with non verified professional
            modes = item['enrollment_modes']
            prof_no_id_mode = modes.pop(enrollment_modes.PROFESSIONAL_NO_ID, {})
            prof_mode = modes[enrollment_modes.PROFESSIONAL]
            for count_key in count_fields:
                prof_mode[count_key] = prof_mode.get(count_key, 0) + prof_no_id_mode.pop(count_key, 0)

            formatted_data.append(item)

        return formatted_data

    @raise_404_if_none
    def get_queryset(self):
        if self.course_ids:
            # create an OR query for course IDs that match
            query = reduce(lambda q, course_id: q | Q(course_id=course_id), self.course_ids, Q())
            queryset = self.model.objects.filter(query)
        else:
            queryset = self.model.objects.all()

        return self.group_by_mode(queryset)
