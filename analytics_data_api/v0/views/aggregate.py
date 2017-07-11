from django.db.models import Sum

from rest_framework.views import APIView
from rest_framework.response import Response

from analytics_data_api.v0.models import CourseMetaSummaryEnrollment


class AggregateDataView(APIView):

    def post(self, request, *args, **kwargs):
        queryset = CourseMetaSummaryEnrollment.objects.all()
        course_ids = dict(request.data).get('course_ids')
        if course_ids:
            queryset = queryset.filter(course_id__in=course_ids)

        data = queryset.aggregate(
            current_enrollment=Sum('count'),
            total_enrollment=Sum('cumulative_count'),
            enrollment_change_7_days=Sum('count_change_7_days')
        )
        data.update(
            queryset.filter(enrollment_mode='verified').aggregate(
                verified_enrollment=Sum('count')
            )
        )
        return Response(data)
