from django.db.models import Sum

from rest_framework.generics import RetrieveAPIView

from analytics_data_api.v1.models import CourseMetaSummaryEnrollment
from analytics_data_api.v1.serializers import CourseTotalsSerializer
from analytics_data_api.v1.views.base import (
    IDsAPIViewMixin,
    PostAsGetAPIViewMixin,
)


class CourseTotalsView(PostAsGetAPIViewMixin, IDsAPIViewMixin, RetrieveAPIView):
    """
    Returns totals of course enrollment statistics.

    **Example Requests**
        GET /api/v1/course_totals/?course_ids={course_id_1},{course_id_2}

        POST /api/v1/course_totals/
        {
            "course_ids": [
                "{course_id_1}",
                "{course_id_2}",
                ...
                "{course_id_200}"
            ]
        }
        ```

    **Parameters**

        For GET requests:
            * Arguments are passed in the query string.
            * List values are passed in as comma-delimited strings.
        For POST requests:
            * Arguments are passed in as a JSON dict in the request body.
            * List values are passed as JSON arrays of strings.

        * course_ids -- List of course ID strings to derive totals from.

    **Response Values**

        Returns enrollment counts and other metadata for each course:

            * count: Total number of learners currently enrolled in the specified courses.
            * cumulative_count: Total number of learners ever enrolled in the specified courses.
            * count_change_7_days: Total change in enrollment across specified courses.
            * verified_enrollment: Total number of leaners currently enrolled as verified in specified courses.
    """
    serializer_class = CourseTotalsSerializer

    # From IDsAPIViewMixin
    ids_param = 'course_ids'

    def get_object(self):
        queryset = CourseMetaSummaryEnrollment.objects.all()
        if self.ids:
            queryset = queryset.filter(course_id__in=self.ids)
        data = queryset.aggregate(
            count=Sum('count'),
            cumulative_count=Sum('cumulative_count'),
            count_change_7_days=Sum('count_change_7_days')
        )
        data.update(
            queryset.filter(enrollment_mode='verified').aggregate(
                verified_enrollment=Sum('count')
            )
        )
        return data
