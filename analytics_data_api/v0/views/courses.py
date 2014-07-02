from rest_framework import generics
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics_data_api.v0.models import CourseActivityByWeek, CourseEnrollmentByBirthYear, CourseEnrollmentByEducation
from analytics_data_api.v0.serializers import CourseActivityByWeekSerializer


class CourseActivityMostRecentWeekView(generics.RetrieveAPIView):
    """
    Counts of users who performed various actions at least once during the most recently computed week.

    The default is all users who performed *any* action in the course.

    The representation has the following fields:

    - course_id: The ID of the course whose activity is described.
    - interval_start: All data from this timestamp up to the `interval_end` was considered when computing this data
      point.
    - interval_end: All data from `interval_start` up to this timestamp was considered when computing this data point.
      Note that data produced at exactly this time is **not** included.
    - label: The type of activity requested. Possible values are:
        - ACTIVE: The number of unique users who performed any action within the course, including actions not
          enumerated below.
        - PLAYED_VIDEO: The number of unique users who started watching any video in the course.
        - ATTEMPTED_PROBLEM: The number of unique users who answered any loncapa based question in the course.
        - POSTED_FORUM: The number of unique users who created a new post, responded to a post, or submitted a comment
          on any forum in the course.
    - count: The number of users who performed the activity indicated by the `label`.

    Parameters:

    - course_id (string): Unique identifier for the course.
    - label (string): The type of activity. Defaults to `ACTIVE`. Possible values:
        - `ACTIVE`
        - `PLAYED_VIDEO`
        - `ATTEMPTED_PROBLEM`
        - `POSTED_FORUM`

    """

    serializer_class = CourseActivityByWeekSerializer

    def get_object(self):  # pylint: disable=arguments-differ
        """Select the activity report for the given course and label."""
        course_id = self.kwargs.get('pk')
        label = self.request.QUERY_PARAMS.get('label', 'ACTIVE')

        try:
            return CourseActivityByWeek.get_most_recent(course_id, label)
        except ObjectDoesNotExist:
            raise Http404


class AbstractCourseEnrollmentView(APIView):
    model = None

    def render_data(self, data):
        raise NotImplementedError('Subclasses must define a render_data method!')

    def get(self, request, *args, **kwargs):
        if not self.model:
            raise NotImplementedError('Subclasses must specify a model!')

        course_id = self.kwargs['pk']
        data = self.model.objects.filter(course_id=course_id)

        if not data:
            raise Http404

        return Response(self.render_data(data))


class CourseEnrollmentByBirthYearView(AbstractCourseEnrollmentView):
    """
    Course enrollment broken down by user birth year

    Returns the enrollment of a course with users broken down by their birth years.
    """

    model = CourseEnrollmentByBirthYear

    def render_data(self, data):
        return {
            'birth_years': dict(data.values_list('birth_year', 'num_enrolled_students'))
        }


class CourseEnrollmentByEducationView(AbstractCourseEnrollmentView):
    model = CourseEnrollmentByEducation

    def render_data(self, data):
        return {
            'education_levels': dict(data.values_list('education_level__short_name', 'num_enrolled_students'))
        }
