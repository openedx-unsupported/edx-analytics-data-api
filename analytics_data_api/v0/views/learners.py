"""
API methods for module level data.
"""
from rest_framework import generics

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

from analytics_data_api.v0.exceptions import (
    CourseNotSpecifiedError, CourseKeyMalformedError, LearnerNotFoundError)
from analytics_data_api.v0.models import RosterEntry
from analytics_data_api.v0.serializers import LearnerSerializer


class CourseViewMixin(object):
    """
    Captures the course_id query arg and validates it.
    """

    course_id = None

    def get(self, request, *args, **kwargs):
        self.course_id = request.QUERY_PARAMS.get('course_id', None)
        if not self.course_id:
            raise CourseNotSpecifiedError()
        try:
            CourseKey.from_string(self.course_id)
        except InvalidKeyError:
            raise CourseKeyMalformedError(course_id=self.course_id)
        return super(CourseViewMixin, self).get(request, *args, **kwargs)


class LearnerView(CourseViewMixin, generics.RetrieveAPIView):
    """
    Get a particular student's data for a particular course.

    **Example Request**

        GET /api/v0/learners/{username}/?course_id={course_id}

    **Response Values**

        Returns viewing data for each segment of a video.  For each segment,
        the collection contains the following data.

            * segment: The order of the segment in the video timeline.
            * num_users: The number of unique users who viewed this segment.
            * num_views: The number of views for this segment.
            * created: The date the segment data was computed.

        Returns the user metadata and engagement data:

            * username: User name.
            * enrollment_mode: Enrollment mode (e.g. "honor).
            * name: User name.
            * email: User email.
            * segments: Classification for this course based on engagement, (e.g. "has_potential").
            * engagements: Summary of engagement events for a time span.
                * videos_viewed: Number of times a video was played.
                * problems_completed: Unique number of problems completed.
                * problems_attempted: Unique number of problems attempted.
                * problem_attempts: Number of attempts of problems.
                * discussions_contributed: Number of discussions (e.g. forum posts).

    **Parameters**

        You can specify course ID for which you want data.

        course_id -- The course within which user data is requested.

    """
    serializer_class = LearnerSerializer
    username = None
    lookup_field = 'username'

    def get(self, request, *args, **kwargs):
        self.username = self.kwargs.get('username')
        return super(LearnerView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        return RosterEntry.get_course_user(self.course_id, self.username)

    def get_object(self, queryset=None):
        queryset = self.get_queryset()
        if len(queryset) == 1:
            return queryset[0]
        raise LearnerNotFoundError(username=self.username, course_id=self.course_id)
