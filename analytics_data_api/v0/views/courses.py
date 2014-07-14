from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from rest_framework import generics
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics_data_api.v0.models import CourseActivityByWeek, CourseEnrollmentByBirthYear, \
    CourseEnrollmentByEducation, CourseEnrollmentByGender, CourseEnrollmentDaily
from analytics_data_api.v0.serializers import CourseActivityByWeekSerializer, CourseEnrollmentDailySerializer


class CourseActivityMostRecentWeekView(generics.RetrieveAPIView):
    """
    Counts of users who performed various actions at least once during the most recently computed week.

    The default is all users who performed <strong>any</strong> action in the course.

    The representation has the following fields:

    <ul>
    <li>course_id: The string identifying the course whose activity is described (e.g. edX/DemoX/Demo_Course).</li>
    - interval_start: All data from this timestamp up to the `interval_end` was considered when computing this data
      point.
    - interval_end: All data from `interval_start` up to this timestamp was considered when computing this data point.
      Note that data produced at exactly this time is **not** included.
    - activity_type: The type of activity requested. Possible values are:
        - ANY: The number of unique users who performed any action within the course, including actions not
          enumerated below.
        - PLAYED_VIDEO: The number of unique users who started watching any video in the course.
        - ATTEMPTED_PROBLEM: The number of unique users who answered any loncapa based question in the course.
        - POSTED_FORUM: The number of unique users who created a new post, responded to a post, or submitted a comment
          on any forum in the course.
    - count: The number of users who performed the activity indicated by the `activity_type`.
    </ul>

    activity_type -- The type of activity. (Defaults to "any".)

    """

    serializer_class = CourseActivityByWeekSerializer

    def get_object(self, queryset=None):
        """Select the activity report for the given course and activity type."""
        course_id = self.kwargs.get('course_id')
        activity_type = self.request.QUERY_PARAMS.get('activity_type', 'any')
        activity_type = activity_type.lower()

        try:
            return CourseActivityByWeek.get_most_recent(course_id, activity_type)
        except ObjectDoesNotExist:
            raise Http404


class AbstractCourseEnrollmentView(APIView):
    model = None

    def render_data(self, data):
        """
        Render view data
        """
        raise NotImplementedError('Subclasses must define a render_data method!')

    def get(self, request, *args, **kwargs):    # pylint: disable=unused-argument
        if not self.model:
            raise NotImplementedError('Subclasses must specify a model!')

        course_id = self.kwargs['course_id']
        data = self.model.objects.filter(course__course_id=course_id)

        if not data:
            raise Http404

        return Response(self.render_data(data))


class CourseEnrollmentByBirthYearView(AbstractCourseEnrollmentView):
    """
    Course enrollment broken down by user birth year

    Returns the enrollment of a course with users binned by their birth years.
    """

    model = CourseEnrollmentByBirthYear

    def render_data(self, data):
        return {
            'birth_years': dict(data.values_list('birth_year', 'count'))
        }


class CourseEnrollmentByEducationView(AbstractCourseEnrollmentView):
    """
    Course enrollment broken down by user level of education

    Returns the enrollment of a course with users binned by their education levels.
    """
    model = CourseEnrollmentByEducation

    def render_data(self, data):
        return {
            'education_levels': dict(data.values_list('education_level__short_name', 'count'))
        }


class CourseEnrollmentByGenderView(AbstractCourseEnrollmentView):
    """
    Course enrollment broken down by user gender

    Returns the enrollment of a course with users binned by their genders.

    Genders:
        m - male
        f - female
        o - other
    """
    model = CourseEnrollmentByGender

    def render_data(self, data):
        return {
            'genders': dict(data.values_list('gender', 'count'))
        }


class CourseEnrollmentLatestView(RetrieveAPIView):
    """ Returns the latest enrollment count for the specified course. """
    model = CourseEnrollmentDaily
    serializer_class = CourseEnrollmentDailySerializer

    def get_object(self, queryset=None):
        try:
            course_id = self.kwargs['course_id']
            return CourseEnrollmentDaily.objects.filter(course__course_id=course_id).order_by('-date')[0]
        except IndexError:
            raise Http404
