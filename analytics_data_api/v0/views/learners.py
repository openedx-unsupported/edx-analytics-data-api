"""
API methods for module level data.
"""
from rest_framework import generics

from analytics_data_api.constants import learner
from analytics_data_api.v0.exceptions import (
    LearnerNotFoundError,
    ParameterValueError,
)
from analytics_data_api.v0.models import RosterEntry
from analytics_data_api.v0.serializers import ElasticsearchDSLSearchSerializer, LearnerSerializer
from analytics_data_api.v0.views import CourseViewMixin
from analytics_data_api.v0.views.utils import split_query_argument


class LearnerView(CourseViewMixin, generics.RetrieveAPIView):
    """
    Get a particular student's data for a particular course.

    **Example Request**

        GET /api/v0/learners/{username}/?course_id={course_id}

    **Response Values**

        Returns the learner metadata and engagement data:

            * username: User's username.
            * enrollment_mode: Enrollment mode (e.g. "honor).
            * name: User's full name.
            * email: User's email.
            * segments: Classification for this course based on engagement, (e.g. "has_potential").
            * engagements: Summary of engagement events for a time span.
                * videos_viewed: Number of times a video was played.
                * problems_completed: Unique number of problems completed.
                * problems_attempted: Unique number of problems attempted.
                * discussions_contributed: Number of discussions (e.g. forum posts).

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
    Get a paginated list of student data for a particular course.

    **Example Request**

        GET /api/v0/learners/?course_id={course_id}

    **Response Values**

        Returns a paginated list of learner metadata and engagement data.
        Pagination data is returned in the top-level of the returned JSON
        object:

            * count: The number of learners matching the query.
            * page: The current one-indexed page number.
            * next: A hyperlink to the next page if one exists, otherwise null.
            * previous: A hyperlink to the previous page if one exists, otherwise null.

        The 'results' key in the returned JSON object maps to an array of
        learners which contains at most a full page's worth of learners.  Each
        learner is a JSON object containing the following keys:

            * username: User's username.
            * enrollment_mode: Enrollment mode (e.g. "honor).
            * name: User's full name.
            * email: User's email.
            * segments: Classification for this course based on engagement, (e.g. "has_potential").
            * engagements: Summary of engagement events for a time span.
                * videos_viewed: Number of times a video was played.
                * problems_completed: Unique number of problems completed.
                * problems_attempted: Unique number of problems attempted.
                * discussions_contributed: Number of discussions (e.g. forum posts).

    **Parameters**

        You can filter the list of learners by course ID and other parameters
        such as enrollment mode and text search.  You can also control the
        page size and page number of the response, as well as sort the learners
        in the response.

        course_id -- The course within which user data is requested.
        page -- The page of results which should be returned.
        page_size -- The maximum number of results which should be returned per page.
        text_search -- A string to search over the name, username, and email of learners.
        segments -- A comma-separated string of segments to which
            learners should belong.  Semgents are "OR"-ed together.
            Cannot use in combination with `ignore_segments`
            argument.
        ignore_segments -- A comma-separated string of segments to
            which learners should NOT belong.  Semgents are "OR"-ed
            together.  Cannot use in combination with `segments`
            argument.
        cohort -- The cohort to which all returned learners must
            belong.
        enrollment_mode -- The enrollment mode to which all returned
            learners must belong.
        order_by -- The field for sorting the response.  Defaults to 'username'.
        sort_order -- The sort direction.  One of 'asc' or 'desc'.
            Defaults to 'asc'.

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
