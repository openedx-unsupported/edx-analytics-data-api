# -*- coding: utf-8 -*-

import copy
import datetime
from itertools import groupby
import json
from urllib import urlencode

import ddt
from django_dynamic_fixture import G
from elasticsearch import Elasticsearch
from mock import patch, Mock
import pytz
from rest_framework import status

from django.conf import settings
from django.core import management

from analyticsdataserver.tests import TestCaseWithAuthentication
from analytics_data_api.constants import engagement_events
from analytics_data_api.v0.models import ModuleEngagementMetricRanges
from analytics_data_api.v0.tests.views import DemoCourseMixin, VerifyCourseIdMixin


class LearnerAPITestMixin(object):
    """Manages an elasticsearch index for testing the learner API."""
    def setUp(self):
        """Creates the index and defines a mapping."""
        super(LearnerAPITestMixin, self).setUp()
        self._es = Elasticsearch([settings.ELASTICSEARCH_LEARNERS_HOST])
        management.call_command('create_elasticsearch_learners_indices')
        self.addCleanup(lambda: management.call_command('delete_elasticsearch_learners_indices'))

    def _create_learner(
            self,
            username,
            course_id,
            name=None,
            email=None,
            enrollment_mode='honor',
            segments=None,
            cohort='Team edX',
            discussion_contributions=0,
            problems_attempted=0,
            problems_completed=0,
            problem_attempts_per_completed=None,
            attempt_ratio_order=0,
            videos_viewed=0,
            enrollment_date='2015-01-28',
    ):
        """Create a single learner roster entry in the elasticsearch index."""
        body = {
            'username': username,
            'course_id': course_id,
            'name': name if name is not None else username,
            'email': email if email is not None else '{}@example.com'.format(username),
            'enrollment_mode': enrollment_mode,
            'discussion_contributions': discussion_contributions,
            'problems_attempted': problems_attempted,
            'problems_completed': problems_completed,
            'attempt_ratio_order': attempt_ratio_order,
            'videos_viewed': videos_viewed,
            'enrollment_date': enrollment_date,
        }

        # leave null fields from being stored in the index.  Otherwise, they will have
        # an explicit null value and we want to test for the case when they're not returned
        optional_fields = [('segments', segments), ('cohort', cohort),
                           ('problem_attempts_per_completed', problem_attempts_per_completed)]
        for optional_field in optional_fields:
            if optional_field[1]:
                body[optional_field[0]] = optional_field[1]

        self._es.create(
            index=settings.ELASTICSEARCH_LEARNERS_INDEX,
            doc_type='roster_entry',
            body=body
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

    def create_update_index(self, date=None):
        """
        Created an index with the date of when the learner index was updated.
        """
        self._es.create(
            index=settings.ELASTICSEARCH_LEARNERS_UPDATE_INDEX,
            doc_type='marker',
            body={
                'date': date,
                'target_index': settings.ELASTICSEARCH_LEARNERS_INDEX,
            }
        )
        self._es.indices.refresh(index=settings.ELASTICSEARCH_LEARNERS_UPDATE_INDEX)


@ddt.ddt
class LearnerTests(VerifyCourseIdMixin, LearnerAPITestMixin, TestCaseWithAuthentication):
    """Tests for the single learner endpoint."""
    path_template = '/api/v0/learners/{}/?course_id={}'

    @ddt.data(
        ('ed_xavier', 'Edward Xavier', 'edX/DemoX/Demo_Course', 'honor', ['has_potential'], 'Team edX',
         43, 3, 6, 0, 8.4, 2, '2015-04-24', '2015-08-05'),
        ('ed_xavier', 'Edward Xavier', 'edX/DemoX/Demo_Course', 'verified'),
    )
    @ddt.unpack
    def test_get_user(self, username, name, course_id, enrollment_mode, segments=None, cohort=None,
                      problems_attempted=None, problems_completed=None, videos_viewed=None,
                      discussion_contributions=None, problem_attempts_per_completed=None,
                      attempt_ratio_order=None, enrollment_date=None, last_updated=None):

        self.create_learners([{
            "username": username,
            "name": name,
            "course_id": course_id,
            "enrollment_mode": enrollment_mode,
            "segments": segments,
            "cohort": cohort,
            "problems_attempted": problems_attempted,
            "problems_completed": problems_completed,
            "videos_viewed": videos_viewed,
            "discussion_contributions": discussion_contributions,
            "problem_attempts_per_completed": problem_attempts_per_completed,
            "attempt_ratio_order": attempt_ratio_order,
            "enrollment_date": enrollment_date,
        }])
        self.create_update_index(last_updated)

        response = self.authenticated_get(self.path_template.format(username, course_id))
        self.assertEquals(response.status_code, 200)

        expected = {
            "username": username,
            "enrollment_mode": enrollment_mode,
            "name": name,
            "email": "{}@example.com".format(username),
            "account_url": "http://lms-host/{}".format(username),
            "segments": segments or [],
            "cohort": cohort,
            "engagements": {
                "problems_attempted": problems_attempted or 0,
                "problems_completed": problems_completed or 0,
                "videos_viewed": videos_viewed or 0,
                "discussion_contributions": discussion_contributions or 0,
                "problem_attempts_per_completed": problem_attempts_per_completed,
            },
            "enrollment_date": enrollment_date,
            "last_updated": last_updated,
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
class LearnerListTests(LearnerAPITestMixin, VerifyCourseIdMixin, TestCaseWithAuthentication):
    """Tests for the learner list endpoint."""
    def setUp(self):
        super(LearnerListTests, self).setUp()
        self.course_id = 'edX/DemoX/Demo_Course'
        self.create_update_index('2015-09-28')

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
        returned_learners = json.loads(response.content)['results']
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
            'cohort': 'alpha',
            "problems_attempted": 43,
            "problems_completed": 3,
            "videos_viewed": 6,
            "discussion_contributions": 0,
            "problem_attempts_per_completed": 23.14,
        }])
        response = self._get(self.course_id)
        self.assert_learners_returned(response, [{
            'username': 'user_1',
            'enrollment_mode': 'honor',
            'segments': ['a', 'b'],
            'cohort': 'alpha',
            "engagements": {
                "problems_attempted": 43,
                "problems_completed": 3,
                "videos_viewed": 6,
                "discussion_contributions": 0,
                "problem_attempts_per_completed": 23.14,
            },
            'last_updated': '2015-09-28',
        }])

    @ddt.data(
        ('segments', ['highly_engaged'], 'segments', 'highly_engaged', True),
        ('segments', ['highly_engaged', 'struggling'], 'segments', 'highly_engaged', True),
        ('segments', ['highly_engaged', 'struggling'], 'segments', 'struggling', True),
        ('segments', ['highly_engaged', 'struggling'], 'segments', 'highly_engaged,struggling', True),
        ('segments', ['highly_engaged', 'struggling'], 'segments', '', True),
        ('segments', ['highly_engaged', 'struggling'], 'segments', 'disengaging', False),
        ('segments', ['highly_engaged'], 'ignore_segments', 'highly_engaged', False),
        ('segments', ['highly_engaged', 'struggling'], 'ignore_segments', 'highly_engaged', False),
        ('segments', ['highly_engaged', 'struggling'], 'ignore_segments', 'struggling', False),
        ('segments', ['highly_engaged', 'struggling'], 'ignore_segments', 'highly_engaged,struggling', False),
        ('segments', ['highly_engaged', 'struggling'], 'ignore_segments', '', True),
        ('segments', ['highly_engaged', 'struggling'], 'ignore_segments', 'disengaging', True),
        ('cohort', 'a', 'cohort', 'a', True),
        ('cohort', 'a', 'cohort', '', True),
        ('cohort', 'a', 'cohort', 'b', False),
        ('cohort', u'Ich möchte Brot zu essen.', 'cohort', u'Ich möchte Brot zu essen.', True),
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
            [{'username': 'a', 'discussion_contributions': 0}, {'username': 'b', 'discussion_contributions': 1}],
            'discussion_contributions', 'asc', [{'username': 'a'}, {'username': 'b'}]
        ),
        (
            [{'username': 'a', 'discussion_contributions': 0}, {'username': 'b', 'discussion_contributions': 1}],
            'discussion_contributions', 'desc', [{'username': 'b'}, {'username': 'a'}]
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
        (
            [{'username': 'a', 'problem_attempts_per_completed': 1.0, 'attempt_ratio_order': 1},
             {'username': 'b', 'problem_attempts_per_completed': 2.0, 'attempt_ratio_order': 10},
             {'username': 'c', 'problem_attempts_per_completed': 2.0, 'attempt_ratio_order': 2},
             {'username': 'd', 'attempt_ratio_order': 0},
             {'username': 'e', 'attempt_ratio_order': -10}],
            'problem_attempts_per_completed', 'asc', [
                {'username': 'a'}, {'username': 'b'}, {'username': 'c'}, {'username': 'd'}, {'username': 'e'}
            ]
        ),
        (
            [{'username': 'a', 'problem_attempts_per_completed': 1.0, 'attempt_ratio_order': 1},
             {'username': 'b', 'problem_attempts_per_completed': 2.0, 'attempt_ratio_order': 10},
             {'username': 'c', 'problem_attempts_per_completed': 2.0, 'attempt_ratio_order': 2},
             {'username': 'd', 'attempt_ratio_order': 0},
             {'username': 'e', 'attempt_ratio_order': -10}],
            'problem_attempts_per_completed', 'desc', [
                {'username': 'e'}, {'username': 'd'}, {'username': 'c'}, {'username': 'b'}, {'username': 'a'}]
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
        ({'course_id': 'edX/DemoX/Demo_Course', 'segments': 'a_non_existent_segment'}, 'illegal_parameter_values'),
        ({'course_id': 'edX/DemoX/Demo_Course', 'ignore_segments': 'a_non_existent_segment'},
         'illegal_parameter_values'),
    )
    @ddt.unpack
    def test_bad_request(self, parameters, expected_error_code):
        response = self.authenticated_get('/api/v0/learners/', parameters)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['error_code'], expected_error_code)


@ddt.ddt
class CourseLearnerMetadataTests(DemoCourseMixin, VerifyCourseIdMixin,
                                 LearnerAPITestMixin, TestCaseWithAuthentication):
    """
    Tests for the course learner metadata endpoint.
    """

    def _get(self, course_id):
        """Helper to send a GET request to the API."""
        return self.authenticated_get('/api/v0/course_learner_metadata/{}/'.format(course_id))

    def get_expected_json(self, segments, enrollment_modes, cohorts):
        expected_json = self._get_full_engagement_ranges()
        expected_json['segments'] = segments
        expected_json['enrollment_modes'] = enrollment_modes
        expected_json['cohorts'] = cohorts
        return expected_json

    def assert_response_matches(self, response, expected_status_code, expected_data):
        self.assertEqual(response.status_code, expected_status_code)
        self.assertDictEqual(json.loads(response.content), expected_data)

    def test_no_course_id(self):
        response = self.authenticated_get('/api/v0/course_learner_metadata/')
        self.assertEqual(response.status_code, 404)

    @ddt.data(
        {},
        {'highly_engaged': 1},
        {'disengaging': 1},
        {'struggling': 1},
        {'inactive': 1},
        {'unenrolled': 1},
        {'highly_engaged': 3, 'disengaging': 1},
        {'disengaging': 10, 'inactive': 12},
        {'highly_engaged': 1, 'disengaging': 2, 'struggling': 3, 'inactive': 4, 'unenrolled': 5},
    )
    def test_segments_unique_learners(self, segments):
        """
        Tests segment counts when each learner belongs to at most one segment.
        """
        learners = [
            {'username': '{}_{}'.format(segment, i), 'course_id': self.course_id, 'segments': [segment]}
            for segment, count in segments.items()
            for i in xrange(count)
        ]
        self.create_learners(learners)
        expected_segments = {"highly_engaged": 0, "disengaging": 0, "struggling": 0, "inactive": 0, "unenrolled": 0}
        expected_segments.update(segments)
        expected = self.get_expected_json(
            segments=expected_segments,
            enrollment_modes={'honor': len(learners)} if learners else {},
            cohorts={'Team edX': len(learners)} if learners else {},
        )
        self.assert_response_matches(self._get(self.course_id), 200, expected)

    def test_segments_same_learner(self):
        """
        Tests segment counts when each learner belongs to multiple segments.
        """
        self.create_learners([
            {'username': 'user_1', 'course_id': self.course_id, 'segments': ['struggling', 'disengaging']},
            {'username': 'user_2', 'course_id': self.course_id, 'segments': ['disengaging']}
        ])
        expected = self.get_expected_json(
            segments={'disengaging': 2, 'struggling': 1, 'highly_engaged': 0, 'inactive': 0, 'unenrolled': 0},
            enrollment_modes={'honor': 2},
            cohorts={'Team edX': 2},
        )
        self.assert_response_matches(self._get(self.course_id), 200, expected)

    @ddt.data(
        [],
        ['honor'],
        ['verified'],
        ['audit'],
        ['nonexistent-enrollment-tracks-still-show-up'],
        ['honor', 'verified', 'audit'],
        ['honor', 'honor', 'verified', 'verified', 'audit', 'audit'],
    )
    def test_enrollment_modes(self, enrollment_modes):
        self.create_learners([
            {'username': 'user_{}'.format(i), 'course_id': self.course_id, 'enrollment_mode': enrollment_mode}
            for i, enrollment_mode in enumerate(enrollment_modes)
        ])
        expected_enrollment_modes = {}
        for enrollment_mode, group in groupby(enrollment_modes):
            # can't call 'len' directly on a group object
            count = len([mode for mode in group])
            expected_enrollment_modes[enrollment_mode] = count
        expected = self.get_expected_json(
            segments={'disengaging': 0, 'struggling': 0, 'highly_engaged': 0, 'inactive': 0, 'unenrolled': 0},
            enrollment_modes=expected_enrollment_modes,
            cohorts={'Team edX': len(enrollment_modes)} if enrollment_modes else {},
        )
        self.assert_response_matches(self._get(self.course_id), 200, expected)

    @ddt.data(
        [],
        ['Yellow'],
        ['Blue'],
        ['Red', 'Red', 'yellow team', 'yellow team', 'green'],
    )
    def test_cohorts(self, cohorts):
        self.create_learners([
            {'username': 'user_{}'.format(i), 'course_id': self.course_id, 'cohort': cohort}
            for i, cohort in enumerate(cohorts)
        ])
        expected_cohorts = {
            cohort: len([mode for mode in group]) for cohort, group in groupby(cohorts)
        }
        expected = self.get_expected_json(
            segments={'disengaging': 0, 'struggling': 0, 'highly_engaged': 0, 'inactive': 0, 'unenrolled': 0},
            enrollment_modes={'honor': len(cohorts)} if cohorts else {},
            cohorts=expected_cohorts,
        )
        self.assert_response_matches(self._get(self.course_id), 200, expected)

    @property
    def empty_engagement_ranges(self):
        """ Returns the engagement ranges where all fields are set to None. """
        empty_engagement_ranges = {
            'engagement_ranges': {
                'date_range': {
                    'start': None,
                    'end': None
                }
            }
        }
        empty_range = {
            range_type: None for range_type in ['class_rank_bottom', 'class_rank_average', 'class_rank_top']
        }
        for metric in engagement_events.EVENTS:
            empty_engagement_ranges['engagement_ranges'][metric] = copy.deepcopy(empty_range)
        return empty_engagement_ranges

    def test_no_engagement_ranges(self):
        response = self._get(self.course_id)
        self.assertEqual(response.status_code, 200)
        self.assertDictContainsSubset(self.empty_engagement_ranges, json.loads(response.content))

    def test_one_engagement_range(self):
        metric_type = 'problems_completed'
        start_date = datetime.datetime(2015, 7, 1, tzinfo=pytz.utc)
        end_date = datetime.datetime(2015, 7, 21, tzinfo=pytz.utc)
        G(ModuleEngagementMetricRanges, course_id=self.course_id, start_date=start_date, end_date=end_date,
          metric=metric_type, range_type='normal', low_value=90, high_value=6120)
        expected_ranges = self.empty_engagement_ranges
        expected_ranges['engagement_ranges'].update({
            'date_range': {
                'start': '2015-07-01',
                'end': '2015-07-21'
            },
            metric_type: {
                'class_rank_bottom': None,
                'class_rank_average': [90.0, 6120.0],
                'class_rank_top': None
            }
        })

        response = self._get(self.course_id)
        self.assertEqual(response.status_code, 200)
        self.assertDictContainsSubset(expected_ranges, json.loads(response.content))

    def _get_full_engagement_ranges(self):
        """ Populates a full set of engagement ranges and returns the expected engagement ranges. """
        start_date = datetime.datetime(2015, 7, 1, tzinfo=pytz.utc)
        end_date = datetime.datetime(2015, 7, 21, tzinfo=pytz.utc)

        expected = {
            'engagement_ranges': {
                'date_range': {
                    'start': '2015-07-01',
                    'end': '2015-07-21'
                }
            }
        }

        max_value = 1000.0
        for metric_type in engagement_events.EVENTS:
            low_ceil = 100.5
            G(ModuleEngagementMetricRanges, course_id=self.course_id, start_date=start_date, end_date=end_date,
              metric=metric_type, range_type='low', low_value=0, high_value=low_ceil)
            normal_floor = 800.8
            G(ModuleEngagementMetricRanges, course_id=self.course_id, start_date=start_date, end_date=end_date,
              metric=metric_type, range_type='normal', low_value=normal_floor, high_value=max_value)

            expected['engagement_ranges'][metric_type] = {
                'class_rank_average': [normal_floor, max_value],
            }
            if metric_type == 'problem_attempts_per_completed':
                expected['engagement_ranges'][metric_type].update({
                    'class_rank_top': [0.0, low_ceil],
                    'class_rank_bottom': None
                })
            else:
                expected['engagement_ranges'][metric_type].update({
                    'class_rank_bottom': [0.0, low_ceil],
                    'class_rank_top': None
                })

        return expected

    def test_engagement_ranges_only(self):
        expected = self._get_full_engagement_ranges()
        response = self._get(self.course_id)
        self.assertEqual(response.status_code, 200)
        self.assertDictContainsSubset(expected, json.loads(response.content))

    def test_engagement_ranges_fields(self):
        expected_events = engagement_events.EVENTS
        response = json.loads(self._get(self.course_id).content)
        self.assertTrue('engagement_ranges' in response)
        for event in expected_events:
            self.assertTrue(event in response['engagement_ranges'])
