import json

from elasticsearch import Elasticsearch
from mock import patch, Mock
from rest_framework import status

from django.conf import settings

from analyticsdataserver.tests import TestCaseWithAuthentication


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

    def create_learners(self, *learners):
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


class LearnerTests(LearnerAPITestMixin, TestCaseWithAuthentication):
    path_template = '/api/v0/learners/{}/?course_id={}'

    def setUp(self):
        super(LearnerTests, self).setUp()
        self.create_learners({
            "username": "ed_xavier",
            "name": "Edward Xavier",
            "course_id": "edX/DemoX/Demo_Course",
            "segments": ["has_potential"],
            "problems_attempted": 43,
            "problems_completed": 3,
            "videos_viewed": 6,
            "discussions_contributed": 0
        })

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
        path = (base_path).format('ed_xavier')
        response = self.authenticated_get(path)
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

        expected = {
            u"error_code": u"course_not_specified",
            u"developer_message": u"Course id/key not specified."
        }
        self.assertDictEqual(json.loads(response.content), expected)

    def test_bad_course_id(self):
        path = self.path_template.format('ed_xavier', 'malformed-course-id')
        response = self.authenticated_get(path)
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        expected = {
            u"error_code": u"course_key_malformed",
            u"developer_message": u"Course id/key malformed-course-id malformed."
        }
        self.assertDictEqual(json.loads(response.content), expected)
