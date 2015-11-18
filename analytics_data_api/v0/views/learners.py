"""
API methods for module level data.
"""
from django.http import Http404
import re
from rest_framework.exceptions import ParseError
from rest_framework import generics

from analytics_data_api.v0.models import RosterEntry
from analytics_data_api.v0.serializers import LearnerSerializer


class CourseViewMixin(object):
    """
    Captures the course_id query arg and validates it.
    """

    COURSE_ID_PATTERN = r'(?P<course_id>[^/+]+[/+][^/+]+[/+][^/]+)'
    course_id = None

    def get(self, request, *args, **kwargs):
        self.course_id = request.QUERY_PARAMS.get('course_id', None)
        if not self.course_id:
            raise ParseError('Course ID was not specified')
        if not re.search(self.COURSE_ID_PATTERN, self.course_id):
            raise ParseError('Course ID malformed')
        return super(CourseViewMixin, self).get(request, *args, **kwargs)


class LearnersListView(CourseViewMixin, generics.ListAPIView):
    """
    TBD

    **Example Request**

        GET TBD

    **Response Values**

        TBD

            * TBD

    **Parameters**

        TBD

    """

    serializer_class = LearnerSerializer
    allow_empty = False

    def get_queryset(self):
        roster = RosterEntry.search().filter('term', course_id=self.course_id).execute()
        return roster


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

            * username: User name
            * enrollment_mode: Enrollment mode, e.g. "honor"
            * name: User name
            * email: User email
            * segments: Classification for this course based on engagement, (e.g. "has_potential")
            * engagement: Summary of engagement events for a time span
                * video_played: Number of times a video was played
                * problem_completed: Number of problems completed
                * problem_attempted: Number of problems attempted
                * forum_commented: Number of forums posts commented
                * forum_responded: Number of forum posts responded
                * forum_created: Number of forum posts created

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
        raise Http404("Object does not exist")
