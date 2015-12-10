import json
from urllib import urlencode

import ddt
from elasticsearch import Elasticsearch
from mock import patch, Mock
from rest_framework import status

from django.conf import settings

from analyticsdataserver.tests import TestCaseWithAuthentication
from analytics_data_api.v0.tests.views import VerifyCourseIdMixin


class LearnerAPITestMixin(object):
    """Manages an elasticsearch index for testing the learner API."""
    def setUp(self):
        """Creates the index and defines a mapping."""
        super(LearnerAPITestMixin, self).setUp()
        self._es = Elasticsearch([settings.ELASTICSEARCH_LEARNERS_HOST])
        self._es.indices.create(index=settings.ELASTICSEARCH_LEARNERS_INDEX)
        self._es.indices.put_mapping(
            index=settings.ELASTICSEARCH_LEARNERS_INDEX,
            doc_type='roster_entry',
            body={
                'properties': {
                    'name': {
                        'type': 'string'
                    },
                    'username': {
                        'type': 'string', 'index': 'not_analyzed'
                    },
                    'email': {
                        'type': 'string', 'index': 'not_analyzed', 'doc_values': True
                    },
                    'course_id': {
                        'type': 'string', 'index': 'not_analyzed'
                    },
                    'enrollment_mode': {
                        'type': 'string', 'index': 'not_analyzed', 'doc_values': True
                    },
                    'segments': {
                        'type': 'string'
                    },
                    'cohort': {
                        'type': 'string', 'index': 'not_analyzed', 'doc_values': True
                    },
                    'discsussions_contributed': {
                        'type': 'integer', 'doc_values': True
                    },
                    'problems_attempted': {
                        'type': 'integer', 'doc_values': True
                    },
                    'problems_completed': {
                        'type': 'integer', 'doc_values': True
                    },
                    'attempts_per_problem_completed': {
                        'type': 'float', 'doc_values': True
                    },
                    'videos_viewed': {
                        'type': 'integer', 'doc_values': True
                    }
                }
            }
        )

    def tearDown(self):
        """Remove the index after every test."""
        super(LearnerAPITestMixin, self).tearDown()
        self._es.indices.delete(index=settings.ELASTICSEARCH_LEARNERS_INDEX)

    def _create_learner(
            self,
            username,
            course_id,
            name=None,
            email=None,
            enrollment_mode='honor',
            segments=None,
            cohort='',
            discussions_contributed=0,
            problems_attempted=0,
            problems_completed=0,
            attempts_per_problem_completed=0,
            videos_viewed=0
    ):
        """Create a single learner roster entry in the elasticsearch index."""
        self._es.create(
            index=settings.ELASTICSEARCH_LEARNERS_INDEX,
            doc_type='roster_entry',
            body={
                'username': username,
                'course_id': course_id,
                'name': name if name is not None else username,
                'email': email if email is not None else '{}@example.com'.format(username),
                'enrollment_mode': enrollment_mode,
                'segments': segments if segments is not None else list(),
                'cohort': cohort,
                'discussions_contributed': discussions_contributed,
                'problems_attempted': problems_attempted,
                'problems_completed': problems_completed,
                'attempts_per_problem_completed': attempts_per_problem_completed,
                'videos_viewed': videos_viewed
            }
        )

    def create_learners(self, learners):
        """
        Creates multiple learner roster entries.  `learners` is a list of
        dicts, each representing a learner which must at least contain
        the keys 'username' and 'course_id'.  Other learner fields can
        be provided as additional keys in the dict - see the mapping
        defined in `setUp`.
        """
        for learner in learners:
            self._create_learner(**learner)
        self._es.indices.refresh(index=settings.ELASTICSEARCH_LEARNERS_INDEX)


class LearnerTests(VerifyCourseIdMixin, LearnerAPITestMixin, TestCaseWithAuthentication):
    """Tests for the single learner endpoint."""
    path_template = '/api/v0/learners/{}/?course_id={}'

    def setUp(self):
        super(LearnerTests, self).setUp()
        self.create_learners([{
            "username": "ed_xavier",
            "name": "Edward Xavier",
            "course_id": "edX/DemoX/Demo_Course",
            "segments": ["has_potential"],
            "problems_attempted": 43,
            "problems_completed": 3,
            "videos_viewed": 6,
            "discussions_contributed": 0
        }])

    def test_get_user(self):
        user_name = 'ed_xavier'
        course_id = 'edX/DemoX/Demo_Course'
        response = self.authenticated_get(self.path_template.format(user_name, course_id))
        self.assertEquals(response.status_code, 200)

        expected = {
            "username": "ed_xavier",
            "enrollment_mode": "honor",
            "name": "Edward Xavier",
            "email": "ed_xavier@example.com",
            "account_url": "http://lms-host/ed_xavier",
            "segments": ["has_potential"],
            "engagements": {
                "problems_attempted": 43,
                "problems_completed": 3,
                "videos_viewed": 6,
                "discussions_contributed": 0
            },
        }
        self.assertDictEqual(expected, response.data)

    @patch('analytics_data_api.v0.models.RosterEntry.get_course_user', Mock(return_value=[]))
    def test_not_found(self):
        user_name = 'a_user'
        course_id = 'edX/DemoX/Demo_Course'
        response = self.authenticated_get(self.path_template.format(user_name, course_id))
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)
        expected = {
            u"error_code": u"no_learner_for_course",
            u"developer_message": u"Learner a_user not found for course edX/DemoX/Demo_Course."
        }
        self.assertDictEqual(json.loads(response.content), expected)

    def test_no_course_id(self):
        base_path = '/api/v0/learners/{}'
        response = self.authenticated_get((base_path).format('ed_xavier'))
        self.verify_no_course_id(response)

    def test_bad_course_id(self):
        path = self.path_template.format('ed_xavier', 'malformed-course-id')
        response = self.authenticated_get(path)
        self.verify_bad_course_id(response)


@ddt.ddt
class LearnerListTests(LearnerAPITestMixin, TestCaseWithAuthentication):
    """Tests for the learner list endpoint."""
    def setUp(self):
        super(LearnerListTests, self).setUp()
        self.course_id = 'edX/DemoX/Demo_Course'

    def _get(self, course_id, **query_params):
        """Helper to send a GET request to the API."""
        query_params['course_id'] = course_id
        return self.authenticated_get('/api/v0/learners/', query_params)

    def assert_learners_returned(self, response, expected_learners):
        """
        Verify that the learners in the response match the expected
        learners, in order.  Each learner in `expected_learners` is a
        dictionary subset of the expected returned representation.  If
        `expected_learners` is None, assert that no learners were
        returned.
        """
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        returned_learners = payload['results']
        if expected_learners is None:
            self.assertEqual(returned_learners, list())
        else:
            self.assertEqual(len(expected_learners), len(returned_learners))
            for expected_learner, returned_learner in zip(expected_learners, returned_learners):
                self.assertDictContainsSubset(expected_learner, returned_learner)

    def test_all_learners(self):
        usernames = ['dan', 'dennis', 'victor', 'olga', 'gabe', 'brian', 'alison']
        self.create_learners([{'username': username, 'course_id': self.course_id} for username in usernames])
        response = self._get(self.course_id)
        # Default ordering is by username
        self.assert_learners_returned(response, [{'username': username} for username in sorted(usernames)])

    def test_course_id(self):
        self.create_learners([
            {'username': 'user_1', 'course_id': self.course_id},
            {'username': 'user_2', 'course_id': 'other/course/id'}
        ])
        response = self._get(self.course_id)
        self.assert_learners_returned(response, [{'username': 'user_1'}])

    def test_data(self):
        self.create_learners([{
            'username': 'user_1',
            'course_id': self.course_id,
            'enrollment_mode': 'honor',
            'segments': ['a', 'b'],
            # TODO: enable during https://openedx.atlassian.net/browse/AN-6319
            # 'cohort': 'alpha',
            "problems_attempted": 43,
            "problems_completed": 3,
            "videos_viewed": 6,
            "discussions_contributed": 0
        }])
        response = self._get(self.course_id)
        self.assert_learners_returned(response, [{
            'username': 'user_1',
            'enrollment_mode': 'honor',
            'segments': ['a', 'b'],
            # TODO: enable during https://openedx.atlassian.net/browse/AN-6319
            # 'cohort': 'alpha',
            "engagements": {
                "problems_attempted": 43,
                "problems_completed": 3,
                "videos_viewed": 6,
                "discussions_contributed": 0
            }
        }])

    @ddt.data(
        ('segments', ['a'], 'segments', 'a', True),
        ('segments', ['a', 'b'], 'segments', 'a', True),
        ('segments', ['a', 'b'], 'segments', 'b', True),
        ('segments', ['a', 'b'], 'segments', 'a,b', True),
        ('segments', ['a', 'b'], 'segments', '', True),
        ('segments', ['a', 'b'], 'segments', 'c', False),
        ('segments', ['a'], 'ignore_segments', 'a', False),
        ('segments', ['a', 'b'], 'ignore_segments', 'a', False),
        ('segments', ['a', 'b'], 'ignore_segments', 'b', False),
        ('segments', ['a', 'b'], 'ignore_segments', 'a,b', False),
        ('segments', ['a', 'b'], 'ignore_segments', '', True),
        ('segments', ['a', 'b'], 'ignore_segments', 'c', True),
        # TODO: enable during https://openedx.atlassian.net/browse/AN-6319
        # ('cohort', 'a', 'cohort', 'a', True),
        # ('cohort', 'a', 'cohort', '', True),
        # ('cohort', 'a', 'cohort', 'b', False),
        ('enrollment_mode', 'a', 'enrollment_mode', 'a', True),
        ('enrollment_mode', 'a', 'enrollment_mode', '', True),
        ('enrollment_mode', 'a', 'enrollment_mode', 'b', False),
        ('name', 'daniel', 'text_search', 'daniel', True),
        ('username', 'daniel', 'text_search', 'daniel', True),
        ('email', 'daniel@example.com', 'text_search', 'daniel@example.com', True),
        ('name', 'daniel', 'text_search', 'dan', False),
        ('email', 'daniel@example.com', 'text_search', 'alfred', False),
    )
    @ddt.unpack
    def test_filters(
            self,
            attribute_name,
            attribute_value,
            filter_key,
            filter_value,
            expect_learner
    ):
        """
        Tests filtering and searching logic.  Sets up a single learner
        with a given attribute value, then makes a GET request to the
        API with the specified query parameter set to the specified
        value.  If `expect_learner` is True, we assert that the user was
        returned, otherwise we assert that no users were returned.
        """
        learner = {'username': 'user', 'course_id': self.course_id}
        learner[attribute_name] = attribute_value
        self.create_learners([learner])
        learner.pop('course_id')
        response = self._get(self.course_id, **{filter_key: filter_value})
        expected_learners = [learner] if expect_learner else None
        self.assert_learners_returned(response, expected_learners)

    @ddt.data(
        ([{'username': 'a'}, {'username': 'b'}], None, None, [{'username': 'a'}, {'username': 'b'}]),
        ([{'username': 'a'}, {'username': 'b'}], None, 'desc', [{'username': 'b'}, {'username': 'a'}]),
        ([{'username': 'a'}, {'username': 'b'}], 'username', 'desc', [{'username': 'b'}, {'username': 'a'}]),
        ([{'username': 'a'}, {'username': 'b'}], 'email', 'asc', [{'username': 'a'}, {'username': 'b'}]),
        ([{'username': 'a'}, {'username': 'b'}], 'email', 'desc', [{'username': 'b'}, {'username': 'a'}]),
        (
            [{'username': 'a', 'discussions_contributed': 0}, {'username': 'b', 'discussions_contributed': 1}],
            'discussions_contributed', 'asc', [{'username': 'a'}, {'username': 'b'}]
        ),
        (
            [{'username': 'a', 'discussions_contributed': 0}, {'username': 'b', 'discussions_contributed': 1}],
            'discussions_contributed', 'desc', [{'username': 'b'}, {'username': 'a'}]
        ),
        (
            [{'username': 'a', 'problems_attempted': 0}, {'username': 'b', 'problems_attempted': 1}],
            'problems_attempted', 'asc', [{'username': 'a'}, {'username': 'b'}]
        ),
        (
            [{'username': 'a', 'problems_attempted': 0}, {'username': 'b', 'problems_attempted': 1}],
            'problems_attempted', 'desc', [{'username': 'b'}, {'username': 'a'}]
        ),
        (
            [{'username': 'a', 'problems_completed': 0}, {'username': 'b', 'problems_completed': 1}],
            'problems_completed', 'asc', [{'username': 'a'}, {'username': 'b'}]
        ),
        (
            [{'username': 'a', 'problems_completed': 0}, {'username': 'b', 'problems_completed': 1}],
            'problems_completed', 'desc', [{'username': 'b'}, {'username': 'a'}]
        ),
        (
            [{'username': 'a', 'videos_viewed': 0}, {'username': 'b', 'videos_viewed': 1}],
            'videos_viewed', 'asc', [{'username': 'a'}, {'username': 'b'}]
        ),
        (
            [{'username': 'a', 'videos_viewed': 0}, {'username': 'b', 'videos_viewed': 1}],
            'videos_viewed', 'desc', [{'username': 'b'}, {'username': 'a'}]
        ),
    )
    @ddt.unpack
    def test_sort(self, learners, order_by, sort_order, expected_users):
        for learner in learners:
            learner['course_id'] = self.course_id
        self.create_learners(learners)
        params = dict()
        if order_by:
            params['order_by'] = order_by
        if sort_order:
            params['sort_order'] = sort_order
        response = self._get(self.course_id, **params)
        self.assert_learners_returned(response, expected_users)

    def test_pagination(self):
        usernames = ['a', 'b', 'c', 'd', 'e']
        expected_page_url_template = 'http://testserver/api/v0/learners/?' \
            '{course_query}&page={page}&page_size={page_size}'
        self.create_learners([{'username': username, 'course_id': self.course_id} for username in usernames])

        response = self._get(self.course_id, page_size=2)
        payload = json.loads(response.content)
        self.assertDictContainsSubset(
            {
                'count': len(usernames),
                'previous': None,
                'next': expected_page_url_template.format(
                    course_query=urlencode({'course_id': self.course_id}), page=2, page_size=2
                ),
                'num_pages': 3
            },
            payload
        )
        self.assert_learners_returned(response, [{'username': 'a'}, {'username': 'b'}])

        response = self._get(self.course_id, page_size=2, page=3)
        payload = json.loads(response.content)
        self.assertDictContainsSubset(
            {
                'count': len(usernames),
                'previous': expected_page_url_template.format(
                    course_query=urlencode({'course_id': self.course_id}), page=2, page_size=2
                ),
                'next': None,
                'num_pages': 3
            },
            payload
        )
        self.assert_learners_returned(response, [{'username': 'e'}])

    # Error cases

    @ddt.data(
        ({}, 'course_not_specified'),
        ({'course_id': ''}, 'course_not_specified'),
        ({'course_id': 'bad_course_id'}, 'course_key_malformed'),
        ({'course_id': 'edX/DemoX/Demo_Course', 'segments': 'a', 'ignore_segments': 'b'}, 'illegal_parameter_values'),
        ({'course_id': 'edX/DemoX/Demo_Course', 'order_by': 'a_non_existent_field'}, 'illegal_parameter_values'),
        ({'course_id': 'edX/DemoX/Demo_Course', 'sort_order': 'bad_value'}, 'illegal_parameter_values'),
        ({'course_id': 'edX/DemoX/Demo_Course', 'page': -1}, 'illegal_parameter_values'),
        ({'course_id': 'edX/DemoX/Demo_Course', 'page': 0}, 'illegal_parameter_values'),
        ({'course_id': 'edX/DemoX/Demo_Course', 'page': 'bad_value'}, 'illegal_parameter_values'),
        ({'course_id': 'edX/DemoX/Demo_Course', 'page_size': 'bad_value'}, 'illegal_parameter_values'),
        ({'course_id': 'edX/DemoX/Demo_Course', 'page_size': 101}, 'illegal_parameter_values'),
    )
    @ddt.unpack
    def test_bad_request(self, parameters, expected_error_code):
        response = self.authenticated_get('/api/v0/learners/', parameters)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['error_code'], expected_error_code)
