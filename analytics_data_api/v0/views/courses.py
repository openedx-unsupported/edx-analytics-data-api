import datetime
from itertools import groupby
import warnings

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max
from django.http import Http404
from django.utils.timezone import make_aware, utc
from rest_framework import generics
from opaque_keys.edx.keys import CourseKey
from analytics_data_api.constants import enrollment_modes

from analytics_data_api.v0 import models, serializers


class BaseCourseView(generics.ListAPIView):
    start_date = None
    end_date = None
    course_id = None
    slug = None

    def get(self, request, *args, **kwargs):
        self.course_id = self.kwargs.get('course_id')
        start_date = request.QUERY_PARAMS.get('start_date')
        end_date = request.QUERY_PARAMS.get('end_date')
        timezone = utc

        if start_date:
            start_date = datetime.datetime.strptime(start_date, settings.DATE_FORMAT)
            start_date = make_aware(start_date, timezone)

        if end_date:
            end_date = datetime.datetime.strptime(end_date, settings.DATE_FORMAT)
            end_date = make_aware(end_date, timezone)

        self.start_date = start_date
        self.end_date = end_date

        return super(BaseCourseView, self).get(request, *args, **kwargs)

    def apply_date_filtering(self, queryset):
        raise NotImplementedError

    def get_queryset(self):
        queryset = self.model.objects.filter(course_id=self.course_id)
        queryset = self.apply_date_filtering(queryset)
        if not queryset:
            raise Http404
        return queryset

    def get_csv_filename(self):
        course_key = CourseKey.from_string(self.course_id)
        course_id = u'-'.join([course_key.org, course_key.course, course_key.run])
        return u'{0}--{1}.csv'.format(course_id, self.slug)

    def finalize_response(self, request, response, *args, **kwargs):
        if request.META.get('HTTP_ACCEPT') == u'text/csv':
            response['Content-Disposition'] = u'attachment; filename={}'.format(self.get_csv_filename())
        return super(BaseCourseView, self).finalize_response(request, response, *args, **kwargs)


# pylint: disable=line-too-long
class CourseActivityWeeklyView(BaseCourseView):
    """
    Weekly course activity

    Returns the course activity. Each row/item will contain all activity types for the course-week.

    <strong>Activity Types</strong>
    <dl>
        <dt>ANY</dt>
        <dd>The number of unique users who performed any action within the course, including actions not enumerated below.</dd>
        <dt>ATTEMPTED_PROBLEM</dt>
        <dd>The number of unique users who answered any loncapa based question in the course.</dd>
        <dt>PLAYED_VIDEO</dt>
        <dd>The number of unique users who started watching any video in the course.</dd>
        <dt>POSTED_FORUM</dt>
        <dd>The number of unique users who created a new post, responded to a post, or submitted a comment on any forum in the course.</dd>
    </dl>

    If no start or end dates are passed, the data for the latest date is returned. All dates are in the UTC zone.

    Data is sorted chronologically (earliest to latest).

    Date format: YYYY-mm-dd (e.g. 2014-01-31)

    start_date --   Date after which all data should be returned (inclusive)
    end_date   --   Date before which all data should be returned (exclusive)
    """

    slug = u'engagement-activity'
    model = models.CourseActivityWeekly
    serializer_class = serializers.CourseActivityWeeklySerializer

    def apply_date_filtering(self, queryset):
        if self.start_date or self.end_date:
            # Filter by start/end date
            if self.start_date:
                queryset = queryset.filter(interval_start__gte=self.start_date)

            if self.end_date:
                queryset = queryset.filter(interval_end__lt=self.end_date)
        else:
            # No date filter supplied, so only return data for the latest date
            latest_date = queryset.aggregate(Max('interval_end'))
            if latest_date:
                latest_date = latest_date['interval_end__max']
                queryset = queryset.filter(interval_end=latest_date)
        return queryset

    def get_queryset(self):
        queryset = super(CourseActivityWeeklyView, self).get_queryset()
        queryset = self.format_data(queryset)
        return queryset

    def _format_activity_type(self, activity_type):
        activity_type = activity_type.lower()

        # The data pipeline stores "any" as "active"; however, the API should display "any".
        if activity_type == 'active':
            activity_type = 'any'

        return activity_type

    def format_data(self, data):
        """
        Group the data by date and combine multiple activity rows into a single row/element.

        Arguments
            data (iterable) -- Data to be formatted.
        """
        formatted_data = []

        for key, group in groupby(data, lambda x: (x.course_id, x.interval_start, x.interval_end)):
            # Iterate over groups and create a single item with all activity types
            item = {
                u'course_id': key[0],
                u'interval_start': key[1],
                u'interval_end': key[2],
                u'created': None
            }

            for activity in group:
                activity_type = self._format_activity_type(activity.activity_type)
                item[activity_type] = activity.count
                item[u'created'] = max(activity.created, item[u'created']) if item[u'created'] else activity.created

            formatted_data.append(item)

        return formatted_data


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

        warnings.warn('CourseActivityMostRecentWeekView has been deprecated! Use CourseActivityWeeklyView instead.',
                      DeprecationWarning)
        course_id = self.kwargs.get('course_id')
        activity_type = self._get_activity_type()

        try:
            return models.CourseActivityWeekly.get_most_recent(course_id, activity_type)
        except ObjectDoesNotExist:
            raise Http404


class BaseCourseEnrollmentView(BaseCourseView):
    def apply_date_filtering(self, queryset):
        if self.start_date or self.end_date:
            # Filter by start/end date
            if self.start_date:
                queryset = queryset.filter(date__gte=self.start_date)

            if self.end_date:
                queryset = queryset.filter(date__lt=self.end_date)
        else:
            # No date filter supplied, so only return data for the latest date
            latest_date = queryset.aggregate(Max('date'))
            if latest_date:
                latest_date = latest_date['date__max']
                queryset = queryset.filter(date=latest_date)
        return queryset


class CourseEnrollmentByBirthYearView(BaseCourseEnrollmentView):
    """
    Course enrollment broken down by user birth year

    Returns the enrollment of a course with users binned by their birth years.

    If no start or end dates are passed, the data for the latest date is returned. All dates are in the UTC zone.

    Data is sorted chronologically (earliest to latest).

    Date format: YYYY-mm-dd (e.g. 2014-01-31)

    start_date --   Date after which all data should be returned (inclusive)
    end_date   --   Date before which all data should be returned (exclusive)
    """

    slug = u'enrollment-age'
    serializer_class = serializers.CourseEnrollmentByBirthYearSerializer
    model = models.CourseEnrollmentByBirthYear


class CourseEnrollmentByEducationView(BaseCourseEnrollmentView):
    """
    Course enrollment broken down by user level of education

    Returns the enrollment of a course with users binned by their education levels.

    If no start or end dates are passed, the data for the latest date is returned. All dates are in the UTC zone.

    Data is sorted chronologically (earliest to latest).

    Date format: YYYY-mm-dd (e.g. 2014-01-31)

    start_date --   Date after which all data should be returned (inclusive)
    end_date   --   Date before which all data should be returned (exclusive)
    """
    slug = u'enrollment-education'
    serializer_class = serializers.CourseEnrollmentByEducationSerializer
    model = models.CourseEnrollmentByEducation


class CourseEnrollmentByGenderView(BaseCourseEnrollmentView):
    """
    Course enrollment broken down by user gender

    Returns the enrollment of a course where each row/item contains user genders for the day.

    If no start or end dates are passed, the data for the latest date is returned. All dates are in the UTC zone.

    Data is sorted chronologically (earliest to latest).

    Date format: YYYY-mm-dd (e.g. 2014-01-31)

    start_date --   Date after which all data should be returned (inclusive)
    end_date   --   Date before which all data should be returned (exclusive)
    """
    slug = u'enrollment-gender'
    serializer_class = serializers.CourseEnrollmentByGenderSerializer
    model = models.CourseEnrollmentByGender

    def get_queryset(self):
        queryset = super(CourseEnrollmentByGenderView, self).get_queryset()
        formatted_data = []

        for key, group in groupby(queryset, lambda x: (x.course_id, x.date)):
            # Iterate over groups and create a single item with gender data
            item = {
                u'course_id': key[0],
                u'date': key[1],
                u'created': None
            }

            for enrollment in group:
                gender = enrollment.cleaned_gender.lower()
                count = item.get(gender, 0)
                count += enrollment.count
                item[gender] = count
                item[u'created'] = max(enrollment.created, item[u'created']) if item[u'created'] else enrollment.created

            formatted_data.append(item)

        return formatted_data


class CourseEnrollmentView(BaseCourseEnrollmentView):
    """
    Returns the enrollment count for the specified course.

    If no start or end dates are passed, the data for the latest date is returned. All dates are in the UTC zone.

    Data is sorted chronologically (earliest to latest).

    Date format: YYYY-mm-dd (e.g. 2014-01-31)

    start_date --   Date after which all data should be returned (inclusive)
    end_date   --   Date before which all data should be returned (exclusive)
    """
    slug = u'enrollment'
    serializer_class = serializers.CourseEnrollmentDailySerializer
    model = models.CourseEnrollmentDaily


class CourseEnrollmentModeView(BaseCourseEnrollmentView):
    """
    Course enrollment broken down by enrollment mode.

    If no start or end dates are passed, the data for the latest date is returned. All dates are in the UTC zone.

    Data is sorted chronologically (earliest to latest).

    Date format: YYYY-mm-dd (e.g. 2014-01-31)

    start_date --   Date after which all data should be returned (inclusive)
    end_date   --   Date before which all data should be returned (exclusive)
    """

    slug = u'enrollment_mode'
    serializer_class = serializers.CourseEnrollmentModeDailySerializer
    model = models.CourseEnrollmentModeDaily

    def get_queryset(self):
        queryset = super(CourseEnrollmentModeView, self).get_queryset()
        formatted_data = []

        for key, group in groupby(queryset, lambda x: (x.course_id, x.date)):
            item = {
                u'course_id': key[0],
                u'date': key[1],
                u'created': None
            }

            total = 0

            for enrollment in group:
                mode = enrollment.mode
                item[mode] = enrollment.count
                item[u'created'] = max(enrollment.created, item[u'created']) if item[u'created'] else enrollment.created
                total += enrollment.count

            # Merge audit and honor
            item[enrollment_modes.HONOR] = item.get(enrollment_modes.HONOR, 0) + item.pop(enrollment_modes.AUDIT, 0)

            item[u'count'] = total

            formatted_data.append(item)

        return formatted_data


# pylint: disable=line-too-long
class CourseEnrollmentByLocationView(BaseCourseEnrollmentView):
    """
    Course enrollment broken down by user location

    Returns the enrollment of a course with users binned by their location. Location is calculated based on the user's
    IP address. Enrollment counts for users whose location cannot be determined will be included in an entry with
    country.name set to UNKNOWN.

    Countries are denoted by their <a href="http://www.iso.org/iso/country_codes/country_codes" target="_blank">ISO 3166 country code</a>.

    If no start or end dates are passed, the data for the latest date is returned. All dates are in the UTC zone.

    Data is sorted chronologically (earliest to latest).

    Date format: YYYY-mm-dd (e.g. 2014-01-31)

    start_date --   Date after which all data should be returned (inclusive)
    end_date   --   Date before which all data should be returned (exclusive)
    """
    slug = u'enrollment-location'
    serializer_class = serializers.CourseEnrollmentByCountrySerializer
    model = models.CourseEnrollmentByCountry

    def get_queryset(self):
        # Get all of the data from the database
        queryset = super(CourseEnrollmentByLocationView, self).get_queryset()
        items = queryset.all()

        # Data must be sorted in order for groupby to work properly
        items = sorted(items, key=lambda x: x.country.alpha2)

        # Items to be returned by this method
        returned_items = []

        # Group data by date, country, and course ID
        for key, group in groupby(items, lambda x: (x.date, x.country.alpha2, x.course_id)):
            count = 0
            date = key[0]
            country_code = key[1]
            course_id = key[2]
            created = None

            for item in group:
                created = max(created, item.created) if created else item.created
                count += item.count

            # pylint: disable=no-value-for-parameter,unexpected-keyword-arg
            returned_items.append(models.CourseEnrollmentByCountry(
                course_id=course_id,
                date=date,
                country_code=country_code,
                count=count,
                created=created
            ))

        # Note: We are returning a list, instead of a queryset. This is
        # acceptable since the consuming code simply expects the returned
        # value to be iterable, not necessarily a queryset.
        return returned_items
