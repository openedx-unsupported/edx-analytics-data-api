"""
API methods for module level data.
"""
from rest_framework import generics, status

from analytics_data_api.v0.exceptions import LearnerEngagementTimelineNotFoundError
from analytics_data_api.v0.models import ModuleEngagement
from analytics_data_api.v0.serializers import EngagementDaySerializer
from analytics_data_api.v0.views import CourseViewMixin


class EngagementTimelineView(CourseViewMixin, generics.ListAPIView):
    """
    Get a particular learner's engagement timeline for a particular course.  Days
    without data will not be returned.

    **Example Request**

        GET /api/v0/engagement_timeline/{username}/?course_id={course_id}

    **Response Values**

        Returns the engagement timeline.

            * days: Array of the learner's daily engagement timeline.
                * problems_attempted: Unique number of unique problems attempted.
                * problems_completed: Unique number of problems completed.
                * discussions_contributed: Number of discussions participated in (e.g. forum posts)
                * videos_viewed: Number of videos watched.

    **Parameters**

        You can specify course ID for which you want data.

        course_id -- The course within which user data is requested.

    """
    serializer_class = EngagementDaySerializer
    username = None
    lookup_field = 'username'

    def list(self, request, *args, **kwargs):
        response = super(EngagementTimelineView, self).list(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            response.data = {'days': response.data}
        return response

    def get(self, request, *args, **kwargs):
        self.username = self.kwargs.get('username')
        return super(EngagementTimelineView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = ModuleEngagement.objects.get_timelines(self.course_id, self.username)
        if len(queryset) == 0:
            raise LearnerEngagementTimelineNotFoundError(username=self.username, course_id=self.course_id)
        return queryset
