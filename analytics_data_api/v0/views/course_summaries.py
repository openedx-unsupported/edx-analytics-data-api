"""
TODO: TBD
"""

from django.db.models import Q

from rest_framework import generics

from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.views.utils import (
    raise_404_if_none,
    split_query_argument,
    validate_course_id,
)


class CourseSummariesView(generics.ListAPIView):
    """
    TBD.

    **Example Request**

        GET /api/v0/course_summaries/?course_ids={course_id},{course_id}

    **Response Values**

       TBD

    **Parameters**

        You can specify the course IDs for which you want data.

        course_ids -- The comma-separated course identifiers for which user data is requested.
        For example, edX/DemoX/Demo_Course,course-v1:edX+DemoX+Demo_2016
    """

    course_ids = None
    fields = None
    serializer_class = serializers.CourseMetaSummaryEnrollmentSerializer
    model = models.CourseMetaSummaryEnrollment

    def get(self, request, *args, **kwargs):
        query_params = self.request.query_params
        self.fields = split_query_argument(query_params.get('fields'))
        self.course_ids = split_query_argument(query_params.get('course_ids'))
        if self.course_ids is not None:
            for course_id in self.course_ids:
                validate_course_id(course_id)

        return super(CourseSummariesView, self).get(request, *args, **kwargs)

    @raise_404_if_none
    def get_queryset(self):
        if self.course_ids:
            # create an OR query for course IDs that match
            query = reduce(lambda q, course_id: q|Q(course_id=course_id), self.course_ids, Q())
            queryset = self.model.objects.filter(query)
        else:
            queryset = self.model.objects.all()
        return queryset
