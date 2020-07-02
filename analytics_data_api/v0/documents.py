
from django.conf import settings
from elasticsearch_dsl import Q, Date, Document, Text, Integer, Keyword, Float

from analytics_data_api.constants import country, genders, learner


class RosterUpdate(Document):
    """
    Index which store last update date of passed index.
    """

    date = Date()
    target_index = Keyword(
        fields={
            'raw': Keyword(),
        }
    )

    class Index:
        name = settings.ELASTICSEARCH_LEARNERS_UPDATE_INDEX
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    @classmethod
    def get_last_updated(cls):
        temp = cls.search().query('match', target_index=settings.ELASTICSEARCH_LEARNERS_INDEX).execute()
        return temp


class RosterEntry(Document):
    """
    Index which store learner information of a course.
    """

    course_id = Keyword(
        fields={
            'raw': Keyword(),
        }
    )
    user_id = Integer(
        fields={
            'raw': Integer(),
        }
    )
    username = Keyword(
        fields={
            'raw': Keyword(),
        }
    )
    name = Keyword(
        fields={
            'raw': Keyword(),
        }
    )
    email = Keyword(
        fields={
            'raw': Keyword(),
        }
    )
    language = Keyword(
        fields={
            'raw': Keyword(),
        }
    )
    location = Keyword(
        fields={
            'raw': Keyword(),
        }
    )
    year_of_birth = Integer(
        fields={
            'raw': Integer(),
        }
    )
    level_of_education = Keyword(
        fields={
            'raw': Keyword(),
        }
    )
    gender = Text(
        fields={
            'raw': Text(),
        }
    )
    mailing_address = Keyword(
        fields={
            'raw': Keyword(),
        }
    )
    city = Keyword(
        fields={
            'raw': Keyword(),
        }
    )
    country = Keyword(
        fields={
            'raw': Keyword(),
        }
    )
    goals = Keyword(
        fields={
            'raw': Keyword(),
        }
    )
    enrollment_mode = Keyword(
        fields={
            'raw': Keyword(),
        }
    )
    cohort = Keyword(
        fields={
            'raw': Keyword(),
        }
    )
    segments = Keyword(
        fields={
            'raw': Keyword(),
        }
    )  # segments is an array/list of strings
    problems_attempted = Integer(
        fields={
            'raw': Integer(),
        }
    )
    problems_completed = Integer(
        fields={
            'raw': Integer(),
        }
    )
    problem_attempts_per_completed = Float(
        fields={
            'raw': Float(),
        }
    )
    # Useful for ordering problem_attempts_per_completed (because results can include null, which is
    # different from zero).  attempt_ratio_order is equal to the number of problem attempts if
    # problem_attempts_per_completed is > 1 and set to -problem_attempts if
    # problem_attempts_per_completed = 1.
    attempt_ratio_order = Integer(
        fields={
            'raw': Integer(),
        }
    )
    discussion_contributions = Integer(
        fields={
            'raw': Integer(),
        }
    )
    videos_watched = Integer(
        fields={
            'raw': Integer(),
        }
    )
    enrollment_date = Date()
    last_updated = Date()

    class Index:
        name = settings.ELASTICSEARCH_LEARNERS_INDEX
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        pass

    @classmethod
    def get_course_user(cls, course_id, username):
        """
        Search learner in course.
        """
        return cls.search().query('match', course_id=course_id).query('match', username=username).execute()

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
        Construct a search query for all users in `course_id` and return
        the Search object.

        sort_policies is an array, where the first element is the primary sort.
        Elements in the array are dicts with fields: order_by (field to sort by)
        and sort_order (either 'asc' or 'desc').  Default to 'username' and 'asc'.

        Raises `ValueError` if both `segments` and `ignore_segments` are provided.
        """

        if not sort_policies:
            sort_policies = [{
                'order_by': None,
                'sort_order': None
            }]
        # set default sort policy to 'username' and 'asc'
        for field, default in [('order_by', 'username'), ('sort_order', 'asc')]:
            if sort_policies[0][field] is None:
                sort_policies[0][field] = default

        # Error handling
        if segments and ignore_segments:
            raise ValueError('Cannot combine `segments` and `ignore_segments` parameters.')
        for segment in (segments or list()) + (ignore_segments or list()):
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
        search.query = Q('bool', must=[Q('match', course_id=course_id)])

        # Filtering/Search
        if segments:
            search.query.must.append(Q('bool', should=[Q('match', segments=segment) for segment in segments]))
        elif ignore_segments:
            for segment in ignore_segments:
                search = search.query(~Q('match', segments=segment))  # pylint: disable=invalid-unary-operand-type
        if cohort:
            search = search.query('match', cohort=cohort)
        if enrollment_mode:
            search = search.query('match', enrollment_mode=enrollment_mode)
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
        search.query = Q('bool', must=[Q('match', course_id=course_id)])
        search.aggs.bucket('enrollment_modes', 'terms', field='enrollment_mode', size=page_size)
        search.aggs.bucket('segments', 'terms', field='segments', size=page_size)
        search.aggs.bucket('cohorts', 'terms', field='cohort', size=page_size)
        response = search.execute()

        # Build up the map of aggregation name to count
        segments = response.aggregations.segments
        enrollment_modes = response.aggregations.enrollment_modes
        cohorts = response.aggregations.cohorts

        aggregations = dict()
        aggregations['enrollment_modes'] = {
            enrollment_mode['key']: enrollment_mode['doc_count']
            for enrollment_mode in enrollment_modes
        }
        aggregations['segments'] = {
            segment['key']: segment['doc_count']
            for segment in segments
        }
        aggregations['cohorts'] = {
            cohort['key']: cohort['doc_count']
            for cohort in cohorts
        }

        # Add default values of 0 for segments with no learners
        for segment in learner.SEGMENTS:
            if segment not in aggregations['segments']:
                aggregations['segments'][segment] = 0
        return aggregations
