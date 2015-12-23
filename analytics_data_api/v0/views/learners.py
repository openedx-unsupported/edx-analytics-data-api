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
    Get data for a particular learner in a particular course.

    **Example Request**

        GET /api/v0/learners/{username}/?course_id={course_id}

    **Response Values**

        Returns metadata and engagement data for the learner in JSON format.

            * username: The username of the enrolled learner.
            * enrollment_mode: The learner's selected learning track (for
              example, "audit" or "verified").
            * name: The learner's full name.
            * email: The learner's email address.
            * segments: Classification, based on engagement, of this learner's
              work in this course (for example, "highly_engaged" or
              "struggling").
            * engagements: Summary of engagement events for a time span.
                * videos_viewed: Number of times any course video was played.
                * problems_completed: Number of unique problems the learner
                  answered correctly.
                * problems_attempted: Number of unique problems attempted.
                  This is a count of the individual problems the learner
                  tried. Each problem in a course can increment this count by
                  a maximum of 1.
                * discussions_contributed: Number of posts, responses, or
                  comments the learner contributed to course discussions.

    **Parameters**

        You can specify the course ID for which you want data.

        course_id -- The course identifier for which user data is requested.
        For example, edX/DemoX/Demo_Course.

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
    Get a paginated list of data for all learners in a course.

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

        The 'results' key in the returned object maps to an array of
        learners that contains, at most, a full page's worth of learners. For
        each learner there is an object that contains the following keys.

            * username: The username of an enrolled learner.
            * enrollment_mode: The learner's selected learning track (for
              example, "audit" or "verified").
            * name: The learner's full name.
            * email: The learner's email address.
            * segments: Classification, based on engagement, of each learner's
              work in this course (for example, "highly_engaged" or
              "struggling").
            * engagements: Summary of engagement events for a time span.
                * videos_viewed: Number of times any course video was played.
                * problems_completed: Number of unique problems the learner
                  answered correctly.
                * problems_attempted: Number of unique problems attempted.
                  This is a count of the individual problems the learner
                  tried. Each problem in a course can increment this count by
                  a maximum of 1.
                * discussions_contributed: Number of posts, responses, or
                  comments the learner contributed to course discussions.

    **Parameters**

        You can filter the list of learners by course ID and by other
        parameters, including enrollment mode and text search. You can also
        control the page size and page number of the response, as well as sort
        the learners in the response.

        course_id -- The course identifier for which user data is requested.
            For example, edX/DemoX/Demo_Course.
        page -- The page of results that should be returned.
        page_size -- The maximum number of results to return per page.
        text_search -- An alphanumeric string that is used to search name,
            username, and email address values to find learners.
        segments -- A comma-separated list of segment names that is used
            to select learners. Only learners who are categorized in at least
            one of the segments are returned. Cannot be used in combination
            with the `ignore_segments` argument.
        ignore_segments -- A comma-separated list of segment names that is
            used to exclude learners. Only learners who are NOT categorized
            in any of the segments are returned. Cannot be used in combination
            with the `segments` argument.
        cohort -- The cohort to which all returned learners must
            belong.
        enrollment_mode -- The learning track to which all returned
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
        Fetches the user list from elasticsearch.  Note that an
        elasticsearch_dsl `Search` object is returned, not an actual
        queryset.
        """
        self._validate_query_params()
        query_params = self.request.QUERY_PARAMS

        order_by = query_params.get('order_by')
        sort_order = query_params.get('sort_order')
        sort_policies = [{
            'order_by': order_by,
            'sort_order': sort_order
        }]

        # Ordering by problem_attempts_per_completed can be ambiguous because
        # values could be infinite (e.g. divide by zero) if no problems were completed.
        # Instead, secondary sorting by attempt_ratio_order will produce a sensible ordering.
        if order_by == 'problem_attempts_per_completed':
            sort_policies.append({
                'order_by': 'attempt_ratio_order',
                'sort_order': 'asc' if sort_order == 'desc' else 'desc'
            })

        params = {
            'segments': split_query_argument(query_params.get('segments')),
            'ignore_segments': split_query_argument(query_params.get('ignore_segments')),
            'cohort': query_params.get('cohort'),
            'enrollment_mode': query_params.get('enrollment_mode'),
            'text_search': query_params.get('text_search'),
            'sort_policies': sort_policies,
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

        Returns the engagement timeline in an array.

            * days: An array of the learner's daily engagement timeline.
                * problems_attempted: Number of unique problems attempted.
                  This is a count of the individual problems the learner
                  tried. Each problem in a course can increment this count by
                  a maximum of 1.
                * problems_completed: Number of unique problems the learner
                  answered correctly.
                * discussions_contributed: Number of posts, responses, or
                  comments the learner contributed to course discussions.
                * videos_viewed: Number of times any course video was played.
                * problem_attempts_per_completed: TBD

    **Parameters**

        You can specify the course ID for which you want data.

        course_id -- The course identifier for which user data is requested.
        For example, edX/DemoX/Demo_Course.

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
    Get metadata about the learners in a course. Includes data on segments,
    cohorts, and enrollment modes. Also includes an engagement rubric.

    **Example Request**

        GET /api/v0/course_learner_metadata/{course_id}/

    **Response Values**

        Returns an object with the following keys.

            * cohorts: An object that maps the names of cohorts in the course
              to the number of learners belonging to those cohorts.
            * segments: An object that maps the names of segments in the course
              to the number of learners belonging to those segments. The
              current set of segments is "highly_engaged", "disengaging",
              "struggling", "inactive", and "unenrolled".
            * enrollment_modes: An object that maps the names of learning
              tracks in the course to the number of learners belonging to those
              tracks. Examples include "audit" and "verified".
            * engagement_ranges: An object containing ranges of learner
              engagement with the courseware. Each range has 'below_average',
              'average', and 'above_average' keys. These keys map to
              two-element arrays, in which the first element is the lower bound
              (inclusive) and the second element is the upper bound
              (exclusive). It has the following keys.
                * date_range: The time period to which this data applies.
                * problems_attempted: Engagement ranges for the number of
                  unique problems tried in the date range.
                * problems_completed: Engagement ranges for the number of
                  unique problems answered correctly in the date range.
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
