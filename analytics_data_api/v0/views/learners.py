"""
API methods for module level data.
"""
import logging

from rest_framework import generics, status

from analytics_data_api.v0.exceptions import (
    LearnerEngagementTimelineNotFoundError,
    LearnerNotFoundError,
    ParameterValueError,
)
from analytics_data_api.v0.models import (
    ModuleEngagement,
    ModuleEngagementMetricRanges,
    RosterEntry,
    RosterUpdate,
)
from analytics_data_api.v0.serializers import (
    CourseLearnerMetadataSerializer,
    EdxPaginationSerializer,
    EngagementDaySerializer,
    LastUpdatedSerializer,
    LearnerSerializer,
)
from analytics_data_api.v0.views import CourseViewMixin, PaginatedHeadersMixin, CsvViewMixin
from analytics_data_api.v0.views.utils import split_query_argument


logger = logging.getLogger(__name__)


class LastUpdateMixin(object):

    @classmethod
    def get_last_updated(cls):
        """ Returns the serialized RosterUpdate last_updated field. """
        roster_update = RosterUpdate.get_last_updated()
        last_updated = {'date': None}
        if len(roster_update) >= 1:
            last_updated = roster_update[0]
        else:
            logger.warn('RosterUpdate not found.')
        return LastUpdatedSerializer(last_updated).data


class LearnerView(LastUpdateMixin, CourseViewMixin, generics.RetrieveAPIView):
    """
    Get data for a particular learner in a particular course.

    **Example Request**

        GET /api/v0/learners/{username}/?course_id={course_id}

    **Response Values**

        Returns metadata and engagement data for the learner in JSON format.

            * username: The username of the enrolled learner.
            * account_url:  URL to learner's account api endpoint.
            * enrollment_mode: The learner's selected learning track (for
              example, "audit" or "verified").
            * name: The learner's full name.
            * email: The learner's email address.
            * user_id: The learner's numeric user ID.
            * language: The learner's preferred language.
            * location: The learner's reported location.
            * year_of_birth: The learner's reported year of birth.
            * level_of_education: The learner's reported level of education.
            * gender: The learner's reported gender.
            * mailing_address: The learner's reported mailing address.
            * city: The learner's reported city.
            * country: The learner's reported country.
            * goals: The learner's reported goals.
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
                * discussion_contributions: Number of posts, responses, or
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

    def retrieve(self, request, *args, **kwargs):
        """
        Adds the last_updated field to the result.
        """
        response = super(LearnerView, self).retrieve(request, args, kwargs)
        response.data.update(self.get_last_updated())
        return response

    def get_queryset(self):
        return RosterEntry.get_course_user(self.course_id, self.username)

    def get_object(self):
        queryset = self.get_queryset()
        if len(queryset) == 1:
            return queryset[0]
        raise LearnerNotFoundError(username=self.username, course_id=self.course_id)


class LearnerListView(LastUpdateMixin, CourseViewMixin, PaginatedHeadersMixin, CsvViewMixin, generics.ListAPIView):
    """
    Get a paginated list of data for all learners in a course.

    **Example Request**

        GET /api/v0/learners/?course_id={course_id}

    **Response Values**

        Returns a paginated list of learner metadata and engagement data.

        Pagination links, if applicable, are returned in the response's header.
        e.g.
            Link: <next_url>; rel="next", <previous_url>; rel="prev";

        Returned results may contain the following fields:

            * username: The username of an enrolled learner.
            * enrollment_mode: The learner's selected learning track (for
              example, "audit" or "verified").
            * name: The learner's full name.
            * email: The learner's email address.
            * user_id: The learner's numeric user ID.
            * language: The learner's preferred language.
            * location: The learner's reported location.
            * year_of_birth: The learner's reported year of birth.
            * level_of_education: The learner's reported level of education.
            * gender: The learner's reported gender.
            * mailing_address: The learner's reported mailing address.
            * city: The learner's reported city.
            * country: The learner's reported country.
            * goals: The learner's reported goals.
            * segments: list of classifications, based on engagement, of each
              learner's work in this course (for example, ["highly_engaged"] or
              ["struggling"]).
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

        JSON:

            The default format is JSON, with pagination data in the top level,
            e.g.:
            {
                "count": 123,               // The number of learners that match the query.
                "page":  2,                 // The current one-indexed page number.
                "next":  "http://...",      // A hyperlink to the next page
                                            //  if one exists, otherwise null.
                "previous": "http://...",   // A hyperlink to the previous page
                                            //  if one exists, otherwise null.
                "results": [                // One results object per learner
                    {
                        "username": "user1",
                        "name": "name1",
                        ...
                    },
                    ...
                ]
            }

        CSV:

            If the request Accept header is 'text/csv', then the returned
            results will be in CSV format.  Field names will be on the first
            line as column headings, with one learner per row, e.g.:

                username,name,email,segments.0,engagements.videos_viewed,...
                user1,name1,user1@example.com,"highly engaged",0,...
                user2,name2,user2@example.com,struggling,1,...

            Use the 'fields' parameter to control the list of fields returned,
            and the order they appear in.

            Fields containing "list" values, like 'segments', are flattened and
            returned in order, e.g., segments.0,segments.1,segments.2,...

            Fields containing "dict" values, like 'engagements', are flattened
            and use the fully-qualified field name in the heading, e.g.,
            engagements.videos_viewed,engagements.problems_completed,...

            Note that pagination data is not included in the main response body;
            see above for details on pagination links in the response header.

    **Parameters**

        You can filter the list of learners by course ID and by other
        parameters, including enrollment mode and text search. You can also
        control the page size and page number of the response, the list of
        returned fields, and sort the learners in the response.

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
        fields -- The list of fields, and their sort order, to return when
            viewing CSV data.  Defaults to the full list of available fields,
            in alphabetical order.
    """
    serializer_class = LearnerSerializer
    pagination_class = EdxPaginationSerializer
    filename_slug = 'learners'

    def list(self, request, *args, **kwargs):
        """
        Adds the last_updated field to the results.
        """
        response = super(LearnerListView, self).list(request, args, kwargs)
        last_updated = self.get_last_updated()
        if response.data['results'] is not None:
            for result in response.data['results']:
                result.update(last_updated)
        return response

    def get_queryset(self):
        """
        Fetches the user list and last updated from elasticsearch returned returned
        as a an array of dicts with fields "learner" and "last_updated".
        """
        query_params = self.request.query_params

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
                * discussion_contributions: Number of times the learner
                  contributed to course discussions through posts, responses,
                  or comments.
                * videos_viewed: Number of times any course video was played.
                * problem_attempts_per_completed: Number of attempts per
                  correctly answered problem.  If no problems were answered
                  correctly, null is returned.

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
        queryset = ModuleEngagement.objects.get_timeline(self.course_id, self.username)
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
              engagement with the courseware. Each range has 'class_rank_bottom',
              'class_rank_average', and 'class_rank_top' keys. These keys map to
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
                * discussion_contributions: Engagement ranges for the number of
                  times learners participated in discussions in the date range.

    """
    serializer_class = CourseLearnerMetadataSerializer

    def get_object(self):
        # Because we're serializing data from both Elasticsearch and MySQL into
        # the same JSON object, we have to pass both sources of data in a dict
        # to our custom course metadata serializer.
        return {
            'es_data': RosterEntry.get_course_metadata(self.course_id),
            'engagement_ranges': ModuleEngagementMetricRanges.objects.filter(course_id=self.course_id)
        }
