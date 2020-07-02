
from django.conf import settings
from elasticsearch_dsl import Date, Document, Float, Integer, Keyword, Q, Short

from analytics_data_api.constants import learner


class RosterUpdate(Document):
    """
    Index which store last update date of passed index.
    """

    date = Date()
    target_index = Keyword()

    class Index:
        name = settings.ELASTICSEARCH_LEARNERS_UPDATE_INDEX
        settings = settings.ELASTICSEARCH_INDEX_SETTINGS

    @classmethod
    def get_last_updated(cls):
        return cls.search().query('term', target_index=settings.ELASTICSEARCH_LEARNERS_INDEX).execute()


class RosterEntry(Document):
    """
    Index which store learner information of a course.
    """

    course_id = Keyword()
    user_id = Integer()
    username = Keyword()
    name = Keyword()
    email = Keyword()
    language = Keyword()
    location = Keyword()
    year_of_birth = Short()
    level_of_education = Keyword()
    gender = Keyword()
    mailing_address = Keyword()
    city = Keyword()
    country = Keyword()
    goals = Keyword()
    enrollment_mode = Keyword()
    cohort = Keyword()
    segments = Keyword()  # segments is an array/list of strings
    problems_attempted = Short()
    problems_completed = Short()
    problem_attempts_per_completed = Float()
    # Useful for ordering problem_attempts_per_completed (because results can include null, which is
    # different from zero).  attempt_ratio_order is equal to the number of problem attempts if
    # problem_attempts_per_completed is > 1 and set to -problem_attempts if
    # problem_attempts_per_completed = 1.
    attempt_ratio_order = Short()
    discussion_contributions = Short()
    enrollment_date = Date()
    videos_viewed = Short()
    last_updated = Date()

    class Index:
        name = settings.ELASTICSEARCH_LEARNERS_INDEX
        settings = settings.ELASTICSEARCH_INDEX_SETTINGS

    @classmethod
    def get_course_user(cls, course_id, username):
        """
        Search learner in course.
        """
        return cls.search().query('term', course_id=course_id).query('term', username=username).execute()

    @classmethod
    def get_users_in_course(
            cls,
            course_id,
            segments=None,
            ignore_segments=None,
            cohort=None,
            enrollment_mode=None,
            text_search=None,
            sort_policies=None,
    ):
        """
        Construct a search query for all users in `course_id` and return the Search object.

        sort_policies is an array, where the first element is the primary sort.
        Elements in the array are dicts with fields: order_by (field to sort by)
        and sort_order (either 'asc' or 'desc').  Default to 'username' and 'asc'.

        Raises `ValueError` if both `segments` and `ignore_segments` are provided.
        """

        if not sort_policies:
            sort_policies = [{'order_by': None, 'sort_order': None}]
        # set default sort policy to 'username' and 'asc'
        for field, default in [('order_by', 'username'), ('sort_order', 'asc')]:
            if sort_policies[0][field] is None:
                sort_policies[0][field] = default

        # Error handling
        if segments and ignore_segments:
            raise ValueError('Cannot combine `segments` and `ignore_segments` parameters.')
        for segment in (segments or []) + (ignore_segments or []):
            if segment not in learner.SEGMENTS:
                raise ValueError("segments/ignore_segments value '{segment}' must be one of: ({segments})".format(
                    segment=segment, segments=', '.join(learner.SEGMENTS)
                ))

        order_by_options = (
            'username', 'email', 'discussion_contributions', 'problems_attempted', 'problems_completed',
            'problem_attempts_per_completed', 'attempt_ratio_order', 'videos_viewed'
        )
        sort_order_options = ('asc', 'desc')
        for sort_policy in sort_policies:
            if sort_policy['order_by'] not in order_by_options:
                raise ValueError("order_by value '{order_by}' must be one of: ({order_by_options})".format(
                    order_by=sort_policy['order_by'], order_by_options=', '.join(order_by_options)
                ))
            if sort_policy['sort_order'] not in sort_order_options:
                raise ValueError("sort_order value '{sort_order}' must be one of: ({sort_order_options})".format(
                    sort_order=sort_policy['sort_order'], sort_order_options=', '.join(sort_order_options)
                ))

        search = cls.search()
        search.query = Q('bool', must=[Q('term', course_id=course_id)])

        # Filtering/Search
        if segments:
            search.query.must.append(Q('bool', should=[Q('term', segments=segment) for segment in segments]))
        elif ignore_segments:
            for segment in ignore_segments:
                search = search.query(~Q('term', segments=segment))  # pylint: disable=invalid-unary-operand-type
        if cohort:
            search = search.query('term', cohort=cohort)
        if enrollment_mode:
            search = search.query('term', enrollment_mode=enrollment_mode)
        if text_search:
            search.query.must.append(Q('multi_match', query=text_search, fields=['name', 'username', 'email']))
        # construct the sort hierarchy
        search_request = search.sort(*[
            {
                sort_policy['order_by']: {
                    'order': sort_policy['sort_order'],
                    # ordering of missing fields
                    'missing': '_last' if sort_policy['sort_order'] == 'asc' else '_first'
                }
            }
            for sort_policy in sort_policies
        ])
        return search_request.execute()

    @classmethod
    def get_course_metadata(cls, course_id):
        """
        Returns the number of students belonging to particular cohorts,
        segments, and enrollment modes within a course.  Returns data in the
        following format:

        {
            'cohorts': {
                <cohort_name>: <learner_count>
            },
            'segments': {
                <segment_name>: <learner_count>
            },
            'enrollment_modes': {
                <enrollment_mode_name>: <learner_count>
            }
        }
        """
        # Use the configured default page size to set the number of aggregate search results.
        page_size = getattr(settings, 'AGGREGATE_PAGE_SIZE', 10)

        search = cls.search()
        search.query = Q('bool', must=[Q('term', course_id=course_id)])
        search.aggs.bucket('enrollment_modes', 'terms', field='enrollment_mode', size=page_size)
        search.aggs.bucket('segments', 'terms', field='segments', size=page_size)
        search.aggs.bucket('cohorts', 'terms', field='cohort', size=page_size)
        response = search.execute().to_dict()

        # Build up the map of aggregation name to count
        aggregations = {
            agg_field: {
                bucket['key']: bucket['doc_count']
                for bucket in agg_item['buckets']
            }
            for agg_field, agg_item in response['aggregations'].items()
        }

        # Add default values of 0 for segments with no learners
        for segment in learner.SEGMENTS:
            if segment not in aggregations['segments']:
                aggregations['segments'][segment] = 0
        return aggregations
