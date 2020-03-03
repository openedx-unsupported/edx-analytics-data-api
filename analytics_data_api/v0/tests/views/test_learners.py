# -*- coding: utf-8 -*-

from __future__ import absolute_import

import copy
import datetime
import json
from itertools import groupby

from django.conf import settings
from django.core import management
from django.test import override_settings
from elasticsearch import Elasticsearch
from rest_framework import status
from six.moves import range, zip
from six.moves.urllib.parse import urlencode  # pylint: disable=import-error

import ddt
from analytics_data_api.constants import engagement_events
from analytics_data_api.v0.models import ModuleEngagementMetricRanges
from analytics_data_api.v0.tests.views import CourseSamples, VerifyCourseIdMixin, VerifyCsvResponseMixin
from analytics_data_api.v0.views import CsvViewMixin, PaginatedHeadersMixin
from analyticsdataserver.tests import TestCaseWithAuthentication
from django_dynamic_fixture import G
from mock import Mock, patch


class LearnerAPITestMixin(CsvViewMixin):
    filename_slug = 'learners'

    """Manages an elasticsearch index for testing the learner API."""
    def setUp(self):
        """Creates the index and defines a mapping."""
        super(LearnerAPITestMixin, self).setUp()
        self._es = Elasticsearch([settings.ELASTICSEARCH_LEARNERS_HOST])
        management.call_command('create_elasticsearch_learners_indices')
        # ensure that the index is ready
        # pylint: disable=unexpected-keyword-arg
        self._es.cluster.health(index=settings.ELASTICSEARCH_LEARNERS_INDEX, wait_for_status='yellow')
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
            user_id=None,
            language=None,
            location=None,
            year_of_birth=None,
            level_of_education=None,
            gender=None,
            mailing_address=None,
            city=None,
            country=None,
            goals=None,
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
            "user_id": user_id,
            "language": language,
            "location": location,
            "year_of_birth": year_of_birth,
            "level_of_education": level_of_education,
            "gender": gender,
            "mailing_address": mailing_address,
            "city": city,
            "country": country,
            "goals": goals,
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

    def expected_page_url(self, course_id, page, page_size):
        """
        Returns a paginated URL for the given parameters.
        As with PageNumberPagination, if page=1, it's omitted from the query string.
        """
        if page is None:
            return None
        course_q = urlencode({'course_id': course_id})
        page_q = '&page={}'.format(page) if page and page > 1 else ''
        page_size_q = '&page_size={}'.format(page_size) if page_size > 0 else ''
        return 'http://testserver/api/v0/learners/?{course_q}{page_q}{page_size_q}'.format(
            course_q=course_q, page_q=page_q, page_size_q=page_size_q,
        )


@ddt.ddt
class LearnerTests(VerifyCourseIdMixin, LearnerAPITestMixin, TestCaseWithAuthentication):
    """Tests for the single learner endpoint."""
    path_template = '/api/v0/learners/{}/?course_id={}'

    @ddt.data(
        ('ed_xavier', 'Edward Xavier', 'edX/DemoX/Demo_Course', 'honor', ['has_potential'], 'Team edX',
         43, 3, 6, 0, 8.4, 2, '2015-04-24', '2015-08-05'),
        ('ed_xavier', 'Edward Xavier', 'edX/DemoX/Demo_Course', 'honor', ['has_potential'], 'Team edX',
         43, 3, 6, 0, 8.4, 2, '2015-04-24', '2015-08-05',
         10, 'French', 'Berlin', 1976, 'Bachelors', 'Male', '123 Sesame St', 'Springfield', 'France',
         'I\'ve always wanted to play the piano.'),
        ('ed_xavier', 'Edward Xavier', 'edX/DemoX/Demo_Course', 'verified'),
    )
    @ddt.unpack
    def test_get_user(self, username, name, course_id, enrollment_mode, segments=None, cohort=None,
                      problems_attempted=None, problems_completed=None, videos_viewed=None,
                      discussion_contributions=None, problem_attempts_per_completed=None,
                      attempt_ratio_order=None, enrollment_date=None, last_updated=None,
                      user_id=None, language=None, location=None,
                      year_of_birth=None, level_of_education=None, gender=None,
                      mailing_address=None, city=None, country=None, goals=None):

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
            "user_id": user_id,
            "language": language,
            "location": location,
            "year_of_birth": year_of_birth,
            "level_of_education": level_of_education,
            "gender": gender,
            "mailing_address": mailing_address,
            "city": city,
            "country": country,
            "goals": goals,
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
            "user_id": user_id,
            "language": language,
            "location": location,
            "year_of_birth": year_of_birth,
            "level_of_education": level_of_education,
            "gender": gender,
            "mailing_address": mailing_address,
            "city": city,
            "country": country,
            "goals": goals,
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
        self.create_learners([{'username': username, 'course_id': self.course_id} for username in usernames])

        response = self._get(self.course_id, page_size=2)
        payload = json.loads(response.content)
        self.assertDictContainsSubset(
            {
                'count': len(usernames),
                'previous': None,
                'next': self.expected_page_url(self.course_id, page=2, page_size=2),
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
                'previous': self.expected_page_url(self.course_id, page=2, page_size=2),
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
        ({'course_id': 'edX/DemoX/Demo_Course', 'page': -1}, 'Invalid page.', 404),
        ({'course_id': 'edX/DemoX/Demo_Course', 'page': 0}, 'Invalid page.', 404),
        ({'course_id': 'edX/DemoX/Demo_Course', 'page': 'bad_value'}, 'Invalid page.', 404),
        ({'course_id': 'edX/DemoX/Demo_Course', 'segments': 'a_non_existent_segment'}, 'illegal_parameter_values'),
        ({'course_id': 'edX/DemoX/Demo_Course', 'ignore_segments': 'a_non_existent_segment'},
         'illegal_parameter_values'),
    )
    @ddt.unpack
    def test_bad_request(self, parameters, expected_error_code, expected_status_code=400):
        response = self.authenticated_get('/api/v0/learners/', parameters)
        self.assertEqual(response.status_code, expected_status_code)
        response_json = json.loads(response.content)
        self.assertEqual(response_json.get('error_code', response_json.get('detail')), expected_error_code)


@ddt.ddt
class LearnerCsvListTests(LearnerAPITestMixin, VerifyCourseIdMixin,
                          VerifyCsvResponseMixin, TestCaseWithAuthentication):
    """Tests for the learner list CSV endpoint."""
    def setUp(self):
        super(LearnerCsvListTests, self).setUp()
        self.course_id = 'edX/DemoX/Demo_Course'
        self.create_update_index('2015-09-28')
        self.path = '/api/v0/learners/'

    def test_empty_csv(self):
        """ Verify the endpoint returns data that has been properly converted to CSV. """
        response = self.authenticated_get(
            self.path,
            dict(course_id=self.course_id),
            True,
            HTTP_ACCEPT='text/csv'
        )
        self.assertCsvResponseIsValid(response, self.get_csv_filename(), [], {'Link': None})

    def test_csv_pagination(self):
        """ Verify the endpoint returns properly paginated CSV data"""

        # Create learners, using a cohort name with a comma, to test escaping.
        usernames = ['victor', 'olga', 'gabe', ]
        commaCohort = 'Lions, Tigers, & Bears'
        self.create_learners([{'username': username, 'course_id': self.course_id, 'cohort': commaCohort}
                              for username in usernames])

        # Set last_updated index date
        last_updated = '2015-09-28'
        self.create_update_index(last_updated)

        # Render CSV with one learner per page
        page_size = 1
        prev_page = None

        for idx, username in enumerate(sorted(usernames)):
            page = idx + 1
            response = self.authenticated_get(
                self.path,
                dict(course_id=self.course_id, page=page, page_size=page_size),
                True,
                HTTP_ACCEPT='text/csv'
            )

            # Construct expected content data
            expected_data = [{
                "username": username,
                "enrollment_mode": 'honor',
                "name": username,
                "email": "{}@example.com".format(username),
                "account_url": "http://lms-host/{}".format(username),
                "cohort": commaCohort,
                "engagements.problems_attempted": 0,
                "engagements.problems_completed": 0,
                "engagements.videos_viewed": 0,
                "engagements.discussion_contributions": 0,
                "engagements.problem_attempts_per_completed": None,
                "enrollment_date": '2015-01-28',
                "last_updated": last_updated,
                "segments": None,
                "user_id": None,
                "language": None,
                "location": None,
                "year_of_birth": None,
                "level_of_education": None,
                "gender": None,
                "mailing_address": None,
                "city": None,
                "country": None,
                "goals": None,
            }]

            # Construct expected links header from pagination data
            prev_url = self.expected_page_url(self.course_id, prev_page, page_size)
            next_page = page + 1
            next_url = None
            if next_page <= len(usernames):
                next_url = self.expected_page_url(self.course_id, next_page, page_size)
            expected_links = PaginatedHeadersMixin.get_paginated_links(dict(next=next_url, previous=prev_url))

            self.assertCsvResponseIsValid(response, self.get_csv_filename(), expected_data, {'Link': expected_links})
            prev_page = page

    @ddt.data(
        # fields deliberately out of alphabetical order
        (['username', 'cohort', 'last_updated', 'email'],
         ['username', 'cohort', 'last_updated', 'email']),
        # valid fields interpersed with invalid fields
        (['foo', 'username', 'bar', 'email', 'name', 'baz'],
         ['username', 'email', 'name']),
        # list fields are returned concatenated as one field,
        # and dict fields are listed separately
        (['segments', 'username', 'engagements.videos_viewed', 'engagements.problems_attempted'],
         ['segments', 'username', 'engagements.videos_viewed', 'engagements.problems_attempted']),
        # empty fields list returns all the fields, in alphabetical order.
        ([],
         ['account_url',
          'city',
          'cohort',
          'country',
          'email',
          'engagements.discussion_contributions',
          'engagements.problem_attempts_per_completed',
          'engagements.problems_attempted',
          'engagements.problems_completed',
          'engagements.videos_viewed',
          'enrollment_date',
          'enrollment_mode',
          'gender',
          'goals',
          'language',
          'last_updated',
          'level_of_education',
          'location',
          'mailing_address',
          'name',
          'segments',
          'user_id',
          'username',
          'year_of_birth']),
    )
    @ddt.unpack
    def test_csv_fields(self, fields, valid_fields):

        # Create learners, using a cohort name with a comma, to test escaping.
        usernames = ['victor', 'olga', 'gabe', ]
        commaCohort = 'Lions, Tigers, & Bears'
        self.create_learners([{'username': username, 'course_id': self.course_id, 'cohort': commaCohort}
                              for username in usernames])

        # Render CSV with given fields list
        response = self.authenticated_get(
            self.path,
            dict(course_id=self.course_id, fields=','.join(fields)),
            True,
            HTTP_ACCEPT='text/csv'
        )

        # Check that response contains the valid fields, in the expected order
        self.assertResponseFields(response, valid_fields)


@ddt.ddt
class CourseLearnerMetadataTests(VerifyCourseIdMixin, LearnerAPITestMixin, TestCaseWithAuthentication,):
    """
    Tests for the course learner metadata endpoint.
    """

    def _get(self, course_id):
        """Helper to send a GET request to the API."""
        return self.authenticated_get('/api/v0/course_learner_metadata/{}/'.format(course_id))

    def get_expected_json(self, course_id, segments, enrollment_modes, cohorts):
        expected_json = self._get_full_engagement_ranges(course_id)
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
        (CourseSamples.course_ids[0], {}),
        (CourseSamples.course_ids[1], {'highly_engaged': 1}),
        (CourseSamples.course_ids[2], {'disengaging': 1}),
        (CourseSamples.course_ids[0], {'struggling': 1}),
        (CourseSamples.course_ids[1], {'inactive': 1}),
        (CourseSamples.course_ids[2], {'unenrolled': 1}),
        (CourseSamples.course_ids[0], {'highly_engaged': 3, 'disengaging': 1}),
        (CourseSamples.course_ids[1], {'disengaging': 10, 'inactive': 12}),
        (CourseSamples.course_ids[2], {'highly_engaged': 1, 'disengaging': 2, 'struggling': 3,
                                       'inactive': 4, 'unenrolled': 5}),
    )
    @ddt.unpack
    def test_segments_unique_learners(self, course_id, segments):
        """
        Tests segment counts when each learner belongs to at most one segment.
        """
        learners = [
            {'username': '{}_{}'.format(segment, i), 'course_id': course_id, 'segments': [segment]}
            for segment, count in segments.items()
            for i in range(count)
        ]
        self.create_learners(learners)
        expected_segments = {"highly_engaged": 0, "disengaging": 0, "struggling": 0, "inactive": 0, "unenrolled": 0}
        expected_segments.update(segments)
        expected = self.get_expected_json(
            course_id=course_id,
            segments=expected_segments,
            enrollment_modes={'honor': len(learners)} if learners else {},
            cohorts={'Team edX': len(learners)} if learners else {},
        )
        self.assert_response_matches(self._get(course_id), 200, expected)

    @ddt.data(*CourseSamples.course_ids)
    def test_segments_same_learner(self, course_id):
        """
        Tests segment counts when each learner belongs to multiple segments.
        """
        self.create_learners([
            {'username': 'user_1', 'course_id': course_id, 'segments': ['struggling', 'disengaging']},
            {'username': 'user_2', 'course_id': course_id, 'segments': ['disengaging']}
        ])
        expected = self.get_expected_json(
            course_id=course_id,
            segments={'disengaging': 2, 'struggling': 1, 'highly_engaged': 0, 'inactive': 0, 'unenrolled': 0},
            enrollment_modes={'honor': 2},
            cohorts={'Team edX': 2},
        )
        self.assert_response_matches(self._get(course_id), 200, expected)

    @ddt.data(
        (CourseSamples.course_ids[0], []),
        (CourseSamples.course_ids[1], ['honor']),
        (CourseSamples.course_ids[2], ['verified']),
        (CourseSamples.course_ids[0], ['audit']),
        (CourseSamples.course_ids[1], ['nonexistent-enrollment-tracks-still-show-up']),
        (CourseSamples.course_ids[2], ['honor', 'verified', 'audit']),
        (CourseSamples.course_ids[0], ['honor', 'honor', 'verified', 'verified', 'audit', 'audit']),
    )
    @ddt.unpack
    def test_enrollment_modes(self, course_id, enrollment_modes):
        self.create_learners([
            {'username': 'user_{}'.format(i), 'course_id': course_id, 'enrollment_mode': enrollment_mode}
            for i, enrollment_mode in enumerate(enrollment_modes)
        ])
        expected_enrollment_modes = {}
        for enrollment_mode, group in groupby(enrollment_modes):
            # can't call 'len' directly on a group object
            count = len([mode for mode in group])
            expected_enrollment_modes[enrollment_mode] = count
        expected = self.get_expected_json(
            course_id=course_id,
            segments={'disengaging': 0, 'struggling': 0, 'highly_engaged': 0, 'inactive': 0, 'unenrolled': 0},
            enrollment_modes=expected_enrollment_modes,
            cohorts={'Team edX': len(enrollment_modes)} if enrollment_modes else {},
        )
        self.assert_response_matches(self._get(course_id), 200, expected)

    @ddt.data(
        (CourseSamples.course_ids[0], []),
        (CourseSamples.course_ids[1], ['Yellow']),
        (CourseSamples.course_ids[2], ['Blue']),
        (CourseSamples.course_ids[0], ['Red', 'Red', 'yellow team', 'yellow team', 'green']),
    )
    @ddt.unpack
    def test_cohorts(self, course_id, cohorts):
        self.create_learners([
            {'username': 'user_{}'.format(i), 'course_id': course_id, 'cohort': cohort}
            for i, cohort in enumerate(cohorts)
        ])
        expected_cohorts = {
            cohort: len([mode for mode in group]) for cohort, group in groupby(cohorts)
        }
        expected = self.get_expected_json(
            course_id=course_id,
            segments={'disengaging': 0, 'struggling': 0, 'highly_engaged': 0, 'inactive': 0, 'unenrolled': 0},
            enrollment_modes={'honor': len(cohorts)} if cohorts else {},
            cohorts=expected_cohorts,
        )
        self.assert_response_matches(self._get(course_id), 200, expected)

    @ddt.data(
        (CourseSamples.course_ids[0], [], {}),
        (CourseSamples.course_ids[1], ['Yellow'], {'Yellow': 1}),
        (CourseSamples.course_ids[1], ['Yellow', 'Green'], {'Yellow': 1, 'Green': 1}),
        (CourseSamples.course_ids[0], ['Red', 'Red', 'yellow team', 'green'], {'Red': 2, 'green': 1}),
    )
    @ddt.unpack
    @override_settings(AGGREGATE_PAGE_SIZE=2)
    def test_cohorts_page_size(self, course_id, cohorts, expected_cohorts):
        """ Ensure that the AGGREGATE_PAGE_SIZE sets the max number of cohorts returned."""

        self.create_learners([
            {'username': 'user_{}'.format(i), 'course_id': course_id, 'cohort': cohort}
            for i, cohort in enumerate(cohorts)
        ])
        expected = self.get_expected_json(
            course_id=course_id,
            segments={'disengaging': 0, 'struggling': 0, 'highly_engaged': 0, 'inactive': 0, 'unenrolled': 0},
            enrollment_modes={'honor': len(cohorts)} if cohorts else {},
            cohorts=expected_cohorts,
        )
        self.assert_response_matches(self._get(course_id), 200, expected)

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

    @ddt.data(*CourseSamples.course_ids)
    def test_no_engagement_ranges(self, course_id):
        response = self._get(course_id)
        self.assertEqual(response.status_code, 200)
        self.assertDictContainsSubset(self.empty_engagement_ranges, json.loads(response.content))

    @ddt.data(*CourseSamples.course_ids)
    def test_one_engagement_range(self, course_id):
        metric_type = 'problems_completed'
        start_date = datetime.date(2015, 7, 1)
        end_date = datetime.date(2015, 7, 21)
        G(ModuleEngagementMetricRanges, course_id=course_id, start_date=start_date, end_date=end_date,
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

        response = self._get(course_id)
        self.assertEqual(response.status_code, 200)
        self.assertDictContainsSubset(expected_ranges, json.loads(response.content))

    def _get_full_engagement_ranges(self, course_id):
        """ Populates a full set of engagement ranges and returns the expected engagement ranges. """
        start_date = datetime.date(2015, 7, 1)
        end_date = datetime.date(2015, 7, 21)

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
            G(ModuleEngagementMetricRanges, course_id=course_id, start_date=start_date, end_date=end_date,
              metric=metric_type, range_type='low', low_value=0, high_value=low_ceil)
            normal_floor = 800.8
            G(ModuleEngagementMetricRanges, course_id=course_id, start_date=start_date, end_date=end_date,
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

    @ddt.data(*CourseSamples.course_ids)
    def test_engagement_ranges_only(self, course_id):
        expected = self._get_full_engagement_ranges(course_id)
        response = self._get(course_id)
        self.assertEqual(response.status_code, 200)
        self.assertDictContainsSubset(expected, json.loads(response.content))

    @ddt.data(*CourseSamples.course_ids)
    def test_engagement_ranges_fields(self, course_id):
        expected_events = engagement_events.EVENTS
        response = json.loads(self._get(course_id).content)
        self.assertTrue('engagement_ranges' in response)
        for event in expected_events:
            self.assertTrue(event in response['engagement_ranges'])
