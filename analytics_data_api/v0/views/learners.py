"""
API methods for module level data.
"""
from rest_framework import generics, status

from analytics_data_api.constants import (
    learner
)
from analytics_data_api.v0.exceptions import (
    LearnerEngagementTimelineNotFoundError,
    LearnerNotFoundError,
    ParameterValueError,
)
from analytics_data_api.v0.models import (
    ModuleEngagement,
    ModuleEngagementMetricRanges,
    RosterEntry
)
from analytics_data_api.v0.serializers import (
    CourseLearnerMetadataSerializer,
    ElasticsearchDSLSearchSerializer,
    EngagementDaySerializer,
    LearnerSerializer,
)
from analytics_data_api.v0.views import CourseViewMixin
from analytics_data_api.v0.views.utils import split_query_argument


class LearnerView(CourseViewMixin, generics.RetrieveAPIView):
    """
    Get a particular learner's data for a particular course.

    **Example Request**

        GET /api/v0/learners/{username}/?course_id={course_id}

    **Response Values**

        Returns metadata and engagement data for the learner.

            * username: User's username.
            * enrollment_mode: Enrollment mode (for example, "verified").
            * name: User's full name.
            * email: User's email address.
            * segments: Classification, based on engagement, of this learner's
              work in this course (for example, "highly_engaged" or
              "struggling").
            * engagements: Summary of engagement events for a time span.
                * videos_viewed: Number of times any course video was played.
                * problems_completed: Number of unique problems the learner answered correctly.
                * problems_attempted: Number of unique problems attempted. This is a count of the different problems the learner tried.
                * discussions_contributed: Number of posts, responses, or
                  comments the learner contributed to course discussions.

    **Parameters**

        You can specify the course ID for which you want data.

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


class LearnerListView(CourseViewMixin, generics.ListAPIView):
    """
    Get a paginated list of learner data for a particular course.

    **Example Request**

        GET /api/v0/learners/?course_id={course_id}

    **Response Values**

        Returns a paginated list of learner metadata and engagement data.
        Pagination data is returned in the top level of the returned JSON
        object.

            * count: The number of learners that match the query.
            * page: The current one-indexed page number.
            * next: A hyperlink to the next page if one exists, otherwise null.
            * previous: A hyperlink to the previous page if one exists,
              otherwise null.

        The 'results' key in the returned JSON object maps to an array of
        learners that contains, at most, a full page's worth of learners. For
        each learner there is a JSON object that contains the following keys.

            * username: User's username.
            * enrollment_mode: Enrollment mode (for example, "verified").
            * name: User's full name.
            * email: User's email.
            * segments: Classification, based on engagement, of each learner's
              work in this course (for example, "highly_engaged" or
              "struggling").
            * engagements: Summary of engagement events for a time span.
                * videos_viewed: Number of times any course video was played.
                * problems_completed: Unique number of problems completed.
                * problems_attempted: Unique number of problems attempted.
                * discussions_contributed: Number of discussion contributions
                  (for example, posts).

    **Parameters**

        You can filter the list of learners by course ID and by other
        parameters, including enrollment mode and text search. You can also
        control the page size and page number of the response, as well as sort
        the learners in the response.

        course_id -- The course for which user data is requested.
        page -- The page of results that should be returned.
        page_size -- The maximum number of results to return per page.
        text_search -- An alphanumeric string that is used to search name,
            username, and email values to find learners.
        segments -- A comma-separated string of segment names that is used
            to select only those learners who are categorized in those
            segments. Segments are connected by OR statements. Cannot be
            used in combination with the `ignore_segments` argument.
        ignore_segments -- A comma-separated string of segment names that is
            used to select only those learners who are NOT categorized
            as belonging to those segments. Segments are connected by OR
            statements. Cannot be used in combination with the `segments`
            argument.
        cohort -- The cohort to which all returned learners must
            belong.
        enrollment_mode -- The enrollment mode to which all returned
            learners must belong.
        order_by -- The field for sorting the response. Defaults to 'username'.
        sort_order -- The sort direction.  One of 'asc' (ascending) or 'desc'
            (descending). Defaults to 'asc'.

    """
    serializer_class = LearnerSerializer
    pagination_serializer_class = ElasticsearchDSLSearchSerializer
    paginate_by_param = 'page_size'
    paginate_by = learner.LEARNER_API_DEFAULT_LIST_PAGE_SIZE
    max_paginate_by = 100  # TODO -- tweak during load testing

    def _validate_query_params(self):
        """Validates various querystring parameters."""
        query_params = self.request.QUERY_PARAMS
        page = query_params.get('page')
        if page:
            try:
                page = int(page)
            except ValueError:
                raise ParameterValueError('Page must be an integer')
            finally:
                if page < 1:
                    raise ParameterValueError(
                        'Page numbers are one-indexed, therefore the page value must be greater than 0'
                    )
        page_size = query_params.get('page_size')
        if page_size:
            try:
                page_size = int(page_size)
            except ValueError:
                raise ParameterValueError('Page size must be an integer')
            finally:
                if page_size > self.max_paginate_by or page_size < 1:
                    raise ParameterValueError('Page size must be in the range [1, {}]'.format(self.max_paginate_by))

    def get_queryset(self):
        """
        Fetches the user list from elasticsearch. Note that an
        elasticsearch_dsl `Search` object is returned, not an actual
        queryset.
        """
        self._validate_query_params()
        query_params = self.request.QUERY_PARAMS
        params = {
            'segments': split_query_argument(query_params.get('segments')),
            'ignore_segments': split_query_argument(query_params.get('ignore_segments')),
            # TODO: enable during https://openedx.atlassian.net/browse/AN-6319
            # 'cohort': query_params.get('cohort'),
            'enrollment_mode': query_params.get('enrollment_mode'),
            'text_search': query_params.get('text_search'),
            'order_by': query_params.get('order_by'),
            'sort_order': query_params.get('sort_order')
        }
        # Remove None values from `params` so that we don't overwrite default
        # parameter values in `get_users_in_course`.
        params = {key: val for key, val in params.items() if val is not None}
        try:
            return RosterEntry.get_users_in_course(self.course_id, **params)
        except ValueError as e:
            raise ParameterValueError(e.message)


class EngagementTimelineView(CourseViewMixin, generics.ListAPIView):
    """
    Get a particular learner's engagement timeline for a particular course.
    Days without data are not returned.

    **Example Request**

        GET /api/v0/engagement_timeline/{username}/?course_id={course_id}

    **Response Values**

        Returns the engagement timeline.

            * days: Array of the learner's daily engagement timeline.
                * problems_attempted: Unique number of problems attempted. This is a count of the different problems the learner tried.
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


class CourseLearnerMetadata(CourseViewMixin, generics.RetrieveAPIView):
    """
    Get metadata for the learners in a course. Includes data on segments,
    cohorts, and enrollment modes, and an engagement rubric.

    **Example Request**

        GET /api/v0/course_learner_metadata/{course_id}/

    **Response Values**

        Returns a JSON object with the following keys.

            * cohorts: An object that maps the names of cohorts in the course
              to the number of learners belonging to those cohorts.
            * segments: An object that maps the names of segments in the course
              to the number of learners belonging to those segments. The
              current set of segments is: "highly_engaged", "disengaging",
              "struggling", "inactive", and "unenrolled".
            * enrollment_modes: An object that maps the names of enrollment
              modes in the course to the number of learners belonging to those
              enrollment modes. Examples include "audit" and "verified".
            * engagement_ranges: An object containing ranges of learner
              engagement with the courseware. Each range has 'below_average',
              'average', and 'above_average' keys. These keys map to
              two-element arrays, in which the first element is the lower bound
              (inclusive) and the second element is the upper bound
              (exclusive). It has the following keys.
                * date_range: The time period to which this data applies.
                * problems_attempted: Engagement ranges for the number of
                  problems attempted in the date range.
                * problems_completed: Engagement ranges for the number of
                  problems completed in the date range.
                * problem_attempts_per_completed: Engagement ranges for the
                  number of problem attempts per completed problem in the date
                  range.
                * discussions_contributed: Engagement ranges for the number of
                  times learners participated in discussions in the date range.

    """
    serializer_class = CourseLearnerMetadataSerializer

    def get_object(self, queryset=None):
        # Because we're serializing data from both Elasticsearch and MySQL into
        # the same JSON object, we have to pass both sources of data in a dict
        # to our custom course metadata serializer.
        return {
            'es_data': RosterEntry.get_course_metadata(self.course_id),
            'engagement_ranges': ModuleEngagementMetricRanges.objects.filter(course_id=self.course_id)
        }
