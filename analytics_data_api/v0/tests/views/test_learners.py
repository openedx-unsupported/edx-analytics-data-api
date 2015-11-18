import json

from elasticsearch_dsl.connections import connections
from mock import patch, Mock
from rest_framework import status

from analyticsdataserver.tests import TestCaseWithAuthentication


class LearnerTests(TestCaseWithAuthentication):
    path_template = '/api/v0/learners/{}/?course_id={}'

    @classmethod
    def get_fixture(cls):
        return {
            "took": 11,
            "_shards": {
                "total": 10,
                "successful": 10,
                "failed": 0
            },
            "hits": {
                "total": 33701,
                "max_score": 7.201823,
                "hits": [{
                    "_index": "roster_1_1",
                    "_type": "roster_entry",
                    "_id": "edX/DemoX/Demo_Course|ed_xavier",
                    "_score": 7.201823,
                    "_source": {
                        "username": "ed_xavier",
                        "enrollment_mode": "honor",
                        "problems_attempted": 43,
                        "problems_completed": 3,
                        "problem_attempts": 0,
                        "course_id": "edX/DemoX/Demo_Course",
                        "videos_viewed": 6,
                        "name": "Edward Xavier",
                        "segments": ["has_potential"],
                        "email": "ed_xavier@example.com"
                    }
                }]
            }
        }

    @classmethod
    def setUpClass(cls):
        # mock the elastic search client
        client = Mock()
        client.search.return_value = cls.get_fixture()
        connections.add_connection('default', client)

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
                "problem_attempts": 0,
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
