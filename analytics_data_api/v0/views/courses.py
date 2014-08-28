import datetime

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max
from django.http import Http404
from rest_framework import generics

from analytics_data_api.v0 import models, serializers


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

    serializer_class = serializers.CourseActivityByWeekSerializer
    DEFAULT_ACTIVITY_TYPE = 'ACTIVE'

    def _format_activity_type(self, activity_type):
        """
        Modify the activity type parameter for use with our data.

        Arguments:
            activity_type (str): String to be formatted
        """
        activity_type = activity_type.upper()

        if activity_type == 'ANY':
            activity_type = self.DEFAULT_ACTIVITY_TYPE
        return activity_type

    def _get_activity_type(self):
        """ Retrieve the activity type from the query string. """

        # Support the old label param
        activity_type = self.request.QUERY_PARAMS.get('label', None)

        activity_type = activity_type or self.request.QUERY_PARAMS.get('activity_type', self.DEFAULT_ACTIVITY_TYPE)
        activity_type = self._format_activity_type(activity_type)

        return activity_type

    def get_object(self, queryset=None):
        """Select the activity report for the given course and activity type."""

        course_id = self.kwargs.get('course_id')
        activity_type = self._get_activity_type()

        try:
            return models.CourseActivityByWeek.get_most_recent(course_id, activity_type)
        except ObjectDoesNotExist:
            raise Http404


class BaseCourseEnrollmentView(generics.ListAPIView):
    def verify_course_exists_or_404(self, course_id):
        if self.model.objects.filter(course_id=course_id).exists():
            return True

        raise Http404

    def apply_date_filtering(self, queryset):
        if 'start_date' in self.request.QUERY_PARAMS or 'end_date' in self.request.QUERY_PARAMS:
            # Filter by start/end date
            start_date = self.request.QUERY_PARAMS.get('start_date')
            if start_date:
                start_date = datetime.datetime.strptime(start_date, settings.DATE_FORMAT)
                queryset = queryset.filter(date__gte=start_date)

            end_date = self.request.QUERY_PARAMS.get('end_date')
            if end_date:
                end_date = datetime.datetime.strptime(end_date, settings.DATE_FORMAT)
                queryset = queryset.filter(date__lt=end_date)
        else:
            # No date filter supplied, so only return data for the latest date
            latest_date = queryset.aggregate(Max('date'))
            if latest_date:
                latest_date = latest_date['date__max']
                queryset = queryset.filter(date=latest_date)
        return queryset

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        self.verify_course_exists_or_404(course_id)
        queryset = self.model.objects.filter(course_id=course_id)
        queryset = self.apply_date_filtering(queryset)
        return queryset


class CourseEnrollmentByBirthYearView(BaseCourseEnrollmentView):
    """
    Course enrollment broken down by user birth year

    Returns the enrollment of a course with users binned by their birth years.

    If no start or end dates are passed, the data for the latest date is returned. All dates should are in the UTC zone.

    Data is sorted chronologically (earliest to latest).

    Date format: YYYY-mm-dd (e.g. 2014-01-31)

    start_date --   Date after which all data should be returned (inclusive)
    end_date   --   Date before which all data should be returned (exclusive)
    """

    serializer_class = serializers.CourseEnrollmentByBirthYearSerializer
    model = models.CourseEnrollmentByBirthYear


class CourseEnrollmentByEducationView(BaseCourseEnrollmentView):
    """
    Course enrollment broken down by user level of education

    Returns the enrollment of a course with users binned by their education levels.

    If no start or end dates are passed, the data for the latest date is returned. All dates should are in the UTC zone.

    Data is sorted chronologically (earliest to latest).

    Date format: YYYY-mm-dd (e.g. 2014-01-31)

    start_date --   Date after which all data should be returned (inclusive)
    end_date   --   Date before which all data should be returned (exclusive)
    """
    serializer_class = serializers.CourseEnrollmentByEducationSerializer
    model = models.CourseEnrollmentByEducation


class CourseEnrollmentByGenderView(BaseCourseEnrollmentView):
    """
    Course enrollment broken down by user gender

    Returns the enrollment of a course with users binned by their genders.

    Genders:
        m - male
        f - female
        o - other

    If no start or end dates are passed, the data for the latest date is returned. All dates should are in the UTC zone.

    Data is sorted chronologically (earliest to latest).

    Date format: YYYY-mm-dd (e.g. 2014-01-31)

    start_date --   Date after which all data should be returned (inclusive)
    end_date   --   Date before which all data should be returned (exclusive)
    """
    serializer_class = serializers.CourseEnrollmentByGenderSerializer
    model = models.CourseEnrollmentByGender


class CourseEnrollmentView(BaseCourseEnrollmentView):
    """
    Returns the enrollment count for the specified course.

    If no start or end dates are passed, the data for the latest date is returned. All dates should are in the UTC zone.

    Data is sorted chronologically (earliest to latest).

    Date format: YYYY-mm-dd (e.g. 2014-01-31)

    start_date --   Date after which all data should be returned (inclusive)
    end_date   --   Date before which all data should be returned (exclusive)
    """

    serializer_class = serializers.CourseEnrollmentDailySerializer
    model = models.CourseEnrollmentDaily


# pylint: disable=line-too-long
class CourseEnrollmentByLocationView(BaseCourseEnrollmentView):
    """
    Course enrollment broken down by user location

    Returns the enrollment of a course with users binned by their location. Location is calculated based on the user's
    IP address.

    Countries are denoted by their <a href="http://www.iso.org/iso/country_codes/country_codes" target="_blank">ISO 3166 country code</a>.

    If no start or end dates are passed, the data for the latest date is returned. All dates should are in the UTC zone.

    Data is sorted chronologically (earliest to latest).

    Date format: YYYY-mm-dd (e.g. 2014-01-31)

    start_date --   Date after which all data should be returned (inclusive)
    end_date   --   Date before which all data should be returned (exclusive)
    """

    serializer_class = serializers.CourseEnrollmentByCountrySerializer
    model = models.CourseEnrollmentByCountry

    def get_queryset(self):
        queryset = super(CourseEnrollmentByLocationView, self).get_queryset()

        # Remove all items where country is None
        items = [item for item in queryset.all() if item.country is not None]

        # Note: We are returning a list, instead of a queryset. This is
        # acceptable since the consuming code simply expects the returned
        # value to be iterable, not necessarily a queryset.
        return items
