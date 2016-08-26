import datetime
from itertools import groupby
import warnings

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import connections
from django.db.models import Max
from django.http import Http404
from django.utils.timezone import make_aware, utc
from rest_framework import generics
from opaque_keys.edx.keys import CourseKey

from analytics_data_api.constants import enrollment_modes
from analytics_data_api.utils import dictfetchall
from analytics_data_api.v0 import models, serializers

from analytics_data_api.v0.views.utils import raise_404_if_none


class BaseCourseView(generics.ListAPIView):
    start_date = None
    end_date = None
    course_id = None
    slug = None
    allow_empty = False

    def get(self, request, *args, **kwargs):
        self.course_id = self.kwargs.get('course_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        timezone = utc

        self.start_date = self.parse_date(start_date, timezone)
        self.end_date = self.parse_date(end_date, timezone)

        return super(BaseCourseView, self).get(request, *args, **kwargs)

    def parse_date(self, date, timezone):
        if date:
            try:
                date = datetime.datetime.strptime(date, settings.DATETIME_FORMAT)
            except ValueError:
                date = datetime.datetime.strptime(date, settings.DATE_FORMAT)
            date = make_aware(date, timezone)
        return date

    def apply_date_filtering(self, queryset):
        raise NotImplementedError

    @raise_404_if_none
    def get_queryset(self):
        queryset = self.model.objects.filter(course_id=self.course_id)
        queryset = self.apply_date_filtering(queryset)
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
    Get counts of users who performed specific activities in a course.

    **Example request**

        GET /api/v0/courses/{course_id}/activity/

    **Response Values**

        Returns a list of key/value pairs for student activities, as well as the
        interval start and end dates and the course ID.

            * any: The number of unique users who performed any action in the
              course, including actions not counted in other categories in the
              response.
            * attempted_problem: The number of unique users who answered any
              loncapa-based problem in the course.
            * played_video: The number of unique users who started watching any
              video in the course.
            * posted_forum: The number of unique users who created a new post,
              responded to a post, or submitted a comment on any discussion in
              the course.
            * interval_start: The time and date at which data started being
              included in returned values.
            * interval_end: The time and date at which data stopped being
              included in returned values.
            * course_id: The ID of the course for which data is returned.
            * created: The date the counts were computed.

    **Parameters**

        You can specify the start and end dates for the time period for which
        you want to get activity.

        You specify dates in the format: YYYY-mm-ddTtttttt; for example,
        ``2014-12-15T000000``.

        If no start or end dates are specified, the data for the week ending on
        the previous day is returned.

        start_date -- Date after which all data is returned (inclusive).

        end_date -- Date before which all data is returned (exclusive).
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
    Get counts of users who performed specific activities at least once during the most recently computed week.

    **Example request**

        GET /api/v0/courses/{course_id}/recent_activity/

    **Response Values**

        Returns a list of key/value pairs for student activities, as well as the
        interval start and end dates and the course ID.

            * activity_type: The type of activity counted. Possible values are:

              * any: The number of unique users who performed any action in the
                course, including actions not counted in other categories in the
                response.
              * attempted_problem: The number of unique users who answered any
                loncapa-based problem in the course.
              * played_video: The number of unique users who started watching
                any video in the course.
              * posted_forum: The number of unique users who created a new post,
                responded to a post, or submitted a comment on any discussion in
                the course.
            * count: The number of unique users who performed the specified
              action.
            * interval_start: The time and date at which data started being
              included in returned values.
            * interval_end: The time and date at which data stopped being
              included in returned values.
            * course_id: The ID of the course for which data is returned.

    **Parameters**

        You can specify the activity type for which you want to get the count.

        activity_type -- The type of activity: any (default), attempted_problem, played_video, posted_forum.

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
        activity_type = self.request.query_params.get('label', None)

        activity_type = activity_type or self.request.query_params.get('activity_type', self.DEFAULT_ACTIVITY_TYPE)
        activity_type = self._format_activity_type(activity_type)

        return activity_type

    def get_object(self):
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
    Get the number of enrolled users by birth year.

    **Example request**

        GET /api/v0/courses/{course_id}/enrollment/birth_year/

    **Response Values**

        Returns an array with a collection for each year in which a user was
        born. Each collection contains:

            * course_id: The ID of the course for which data is returned.
            * date: The date for which the enrollment count was computed.
            * birth_year: The birth year for which the enrollment count applies.
            * count: The number of users who were born in the specified year.
            * created: The date the count was computed.

    **Parameters**

        You can specify the start and end dates for which to count enrolled
        users.

        You specify dates in the format: YYYY-mm-dd; for example,
        ``2014-12-15``.

        If no start or end dates are specified, the data for the previous day is
        returned.

        start_date -- Date after which enrolled students are counted (inclusive).

        end_date -- Date before which enrolled students are counted (exclusive).
    """

    slug = u'enrollment-age'
    serializer_class = serializers.CourseEnrollmentByBirthYearSerializer
    model = models.CourseEnrollmentByBirthYear


class CourseEnrollmentByEducationView(BaseCourseEnrollmentView):
    """
    Get the number of enrolled users by education level.

    **Example request**

        GET /api/v0/courses/{course_id}/enrollment/education/

    **Response Values**

        Returns a collection for each level of education reported by a user.
        Each collection contains:

            * course_id: The ID of the course for which data is returned.
            * date: The date for which the enrollment count was computed.
            * education_level: The education level for which the enrollment
              count applies.
            * count: The number of userswho reported the specified education
              level.
            * created: The date the count was computed.

    **Parameters**

        You can specify the start and end dates for which to count enrolled
        users.

        You specify dates in the format: YYYY-mm-dd; for
        example, ``2014-12-15``.

        If no start or end dates are specified, the data for the previous day is
        returned.

        start_date -- Date after which enrolled students are counted (inclusive).

        end_date -- Date before which enrolled students are counted (exclusive).
    """
    slug = u'enrollment-education'
    serializer_class = serializers.CourseEnrollmentByEducationSerializer
    model = models.CourseEnrollmentByEducation


class CourseEnrollmentByGenderView(BaseCourseEnrollmentView):
    """
    Get the number of enrolled users by gender.

    **Example request**

        GET /api/v0/courses/{course_id}/enrollment/gender/

    **Response Values**

        Returns the count of each gender specified by users:

            * course_id: The ID of the course for which data is returned.
            * date: The date for which the enrollment count was computed.
            * female: The count of self-identified female users.
            * male: The count of self-identified male users.
            * other: The count of self-identified other users.
            * unknown: The count of users who did not specify a gender.
            * created: The date the counts were computed.

    **Parameters**

        You can specify the start and end dates for which to count enrolled
        users.

        You specify dates in the format: YYYY-mm-dd; for
        example, ``2014-12-15``.

        If no start or end dates are specified, the data for the previous day is
        returned.

        start_date -- Date after which enrolled students are counted (inclusive).

        end_date -- Date before which enrolled students are counted (exclusive).
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
                u'created': None,
                u'male': 0,
                u'female': 0,
                u'other': 0,
                u'unknown': 0
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
    Get the number of enrolled users.

    **Example request**

        GET /api/v0/courses/{course_id}/enrollment/

    **Response Values**

        Returns the count of enrolled users:

            * course_id: The ID of the course for which data is returned.
            * date: The date for which the enrollment count was computed.
            * count: The count of enrolled users.
            * created: The date the count was computed.

    **Parameters**

        You can specify the start and end dates for which to count enrolled
        users.

        You specify dates in the format: YYYY-mm-dd; for
        example, ``2014-12-15``.

        If no start or end dates are specified, the data for the previous day is
        returned.

        start_date -- Date after which enrolled students are counted (inclusive).

        end_date -- Date before which enrolled students are counted (exclusive).
    """
    slug = u'enrollment'
    serializer_class = serializers.CourseEnrollmentDailySerializer
    model = models.CourseEnrollmentDaily


class CourseEnrollmentModeView(BaseCourseEnrollmentView):
    """
    Get the number of enrolled users by enrollment mode.

    **Example request**

        GET /api/v0/courses/{course_id}/enrollment/mode/

    **Response Values**

        Returns the counts of users by mode:

            * course_id: The ID of the course for which data is returned.
            * date: The date for which the enrollment count was computed.
            * count: The count of currently enrolled users.
            * cumulative_count: The cumulative total of all users ever enrolled.
            * created: The date the counts were computed.
            * honor: The number of users currently enrolled in honor code mode.
            * professional: The number of users currently enrolled in professional mode.
            * verified: The number of users currently enrolled in verified mode.

    **Parameters**

        You can specify the start and end dates for which to count enrolled
        users.

        You specify dates in the format: YYYY-mm-dd; for
        example, ``2014-12-15``.

        If no start or end dates are specified, the data for the previous day is
        returned.

        start_date -- Date after which enrolled students are counted (inclusive).

        end_date -- Date before which enrolled students are counted (exclusive).
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
            cumulative_total = 0

            for enrollment in group:
                mode = enrollment.mode
                item[mode] = enrollment.count
                item[u'created'] = max(enrollment.created, item[u'created']) if item[u'created'] else enrollment.created
                total += enrollment.count
                cumulative_total += enrollment.cumulative_count

            # Merge professional with non verified professional
            item[enrollment_modes.PROFESSIONAL] = \
                item.get(enrollment_modes.PROFESSIONAL, 0) + item.pop(enrollment_modes.PROFESSIONAL_NO_ID, 0)

            item[u'count'] = total
            item[u'cumulative_count'] = cumulative_total

            formatted_data.append(item)

        return formatted_data


# pylint: disable=line-too-long
class CourseEnrollmentByLocationView(BaseCourseEnrollmentView):
    """
    Get the number of enrolled users by location.

    Location is calculated based on the user's IP address. Users whose location
    cannot be determined are counted as having a country.name of UNKNOWN.

    Countries are denoted by their ISO 3166 country code.

    **Example request**

        GET /api/v0/courses/{course_id}/enrollment/location/

    **Response Values**

        Returns counts of genders specified by users:

            * course_id: The ID of the course for which data is returned.
            * date: The date for which the enrollment count was computed.
            * country: Contains the following fields:

              * alpha2: The two-letter country code.
              * alpha3: The three-letter country code.
              * name: The country name.
            * count: The count of users from the country.
            * created: The date the count was computed.

    **Parameters**

        You can specify the start and end dates for which to count enrolled
        users.

        You specify dates in the format: YYYY-mm-dd; for
        example, ``2014-12-15``.

        If no start or end dates are specified, the data for the previous day is
        returned.

        start_date -- Date after which enrolled students are counted (inclusive).

        end_date -- Date before which enrolled students are counted (exclusive).
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


# pylint: disable=abstract-method
class ProblemsListView(BaseCourseView):
    """
    Get the problems.

    **Example request**

        GET /api/v0/courses/{course_id}/problems/

    **Response Values**

        Returns a collection of submission counts and part IDs for each problem. Each collection contains:

            * module_id: The ID of the problem.
            * total_submissions: Total number of submissions.
            * correct_submissions: Total number of *correct* submissions.
            * part_ids: List of problem part IDs.
    """
    serializer_class = serializers.ProblemSerializer
    allow_empty = False

    @raise_404_if_none
    def get_queryset(self):
        # last_response_count is the number of submissions for the problem part and must
        # be divided by the number of problem parts to get the problem submission rather
        # than the problem *part* submissions
        aggregation_query = """
SELECT
    module_id,
    SUM(last_response_count)/COUNT(DISTINCT part_id) AS total_submissions,
    SUM(CASE WHEN correct=1 THEN last_response_count ELSE 0 END)/COUNT(DISTINCT part_id) AS correct_submissions,
    GROUP_CONCAT(DISTINCT part_id) AS part_ids,
    MAX(created) AS created
FROM answer_distribution
WHERE course_id = %s
GROUP BY module_id;
        """

        connection = connections[settings.ANALYTICS_DATABASE]
        with connection.cursor() as cursor:
            if connection.vendor == 'mysql':
                # The default value of group_concat_max_len, 1024, is too low for some course data. Increase this value
                # to its maximum possible value. For more information see
                # http://code.openark.org/blog/mysql/those-oversized-undersized-variables-defaults.
                cursor.execute("SET @@group_concat_max_len = @@max_allowed_packet;")

                cursor.execute("DESCRIBE answer_distribution;")
                column_names = [row[0] for row in cursor.fetchall()]
            # Alternate query for sqlite test database
            else:
                cursor.execute("PRAGMA table_info(answer_distribution)")
                column_names = [row[1] for row in cursor.fetchall()]

            if u'last_response_count' in column_names:
                cursor.execute(aggregation_query, [self.course_id])
            else:
                cursor.execute(aggregation_query.replace('last_response_count', 'count'), [self.course_id])

            rows = dictfetchall(cursor)

        for row in rows:
            # Convert the comma-separated list into an array of strings.
            row['part_ids'] = row['part_ids'].split(',')

            # Convert the aggregated decimal fields to integers
            row['total_submissions'] = int(row['total_submissions'])
            row['correct_submissions'] = int(row['correct_submissions'])

            # Rather than write custom SQL for the SQLite backend, simply parse the timestamp.
            created = row['created']
            if not isinstance(created, datetime.datetime):
                row['created'] = datetime.datetime.strptime(created, '%Y-%m-%d %H:%M:%S')

        return rows


# pylint: disable=abstract-method
class ProblemsAndTagsListView(BaseCourseView):
    """
    Get the problems with the connected tags.

    **Example request**

        GET /api/v0/courses/{course_id}/problems_and_tags/

    **Response Values**

        Returns a collection of submission counts and tags for each problem. Each collection contains:

            * module_id: The ID of the problem.
            * total_submissions: Total number of submissions.
            * correct_submissions: Total number of *correct* submissions.
            * tags: Dictionary that contains pairs "tag key: tag value".
    """
    serializer_class = serializers.ProblemsAndTagsSerializer
    allow_empty = False
    model = models.ProblemsAndTags

    @raise_404_if_none
    def get_queryset(self):
        queryset = self.model.objects.filter(course_id=self.course_id)
        items = queryset.all()

        result = {}

        for v in items:
            if v.module_id in result:
                result[v.module_id]['tags'][v.tag_name] = v.tag_value
                if result[v.module_id]['created'] < v.created:
                    result[v.module_id]['created'] = v.created
            else:
                result[v.module_id] = {
                    'module_id': v.module_id,
                    'total_submissions': v.total_submissions,
                    'correct_submissions': v.correct_submissions,
                    'tags': {
                        v.tag_name: v.tag_value
                    },
                    'created': v.created
                }

        return result.values()


class VideosListView(BaseCourseView):
    """
    Get data for the videos in a course.

    **Example request**

        GET /api/v0/courses/{course_id}/videos/

    **Response Values**

        Returns a collection of video views and metadata for each video.
        For each video, the collection the following data.

            * video_id: The ID of the video.
            * encoded_module_id: The encoded module ID.
            * duration: The length of the video in seconds.
            * segment_length: The length of each segment of the video in seconds.
            * users_at_start: The number of viewers at the start of the video.
            * users_at_end: The number of viewers at the end of the video.
            * created: The date the video data was updated.
    """

    serializer_class = serializers.VideoSerializer
    allow_empty = False
    model = models.Video

    def apply_date_filtering(self, queryset):
        # no date filtering for videos -- just return the queryset
        return queryset
