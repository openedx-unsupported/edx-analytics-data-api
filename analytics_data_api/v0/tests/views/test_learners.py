from elasticsearch_dsl.connections import connections
from mock import patch, Mock

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
                        "problem_attempted": 43,
                        "problem_completed": 3,
                        "forum_created": 0,
                        "course_id": "edX/DemoX/Demo_Course",
                        "video_played": 6,
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
            "segments": ["has_potential"],
            "engagement": {
                "forum_commented": 0,
                "forum_responded": 0,
                "problem_attempted": 43,
                "problem_completed": 3,
                "video_played": 6,
                "forum_created": 0
            }
        }
        from pprint import pprint
        pprint(response.data)
        self.assertDictEqual(expected, response.data)

    @patch('analytics_data_api.v0.models.RosterEntry.get_course_user', Mock(return_value=[]))
    def test_not_found(self):
        user_name = 'a_user'
        course_id = 'edX/DemoX/Demo_Course'
        response = self.authenticated_get(self.path_template.format(user_name, course_id))
        self.assertEquals(response.status_code, 404)

    def test_get_400(self):
        base_path = '/api/v0/learners/{}'
        path = (base_path).format('ed_xavier')
        response = self.authenticated_get(path)
        self.assertEquals(response.status_code, 400)

        path = self.path_template.format('ed_xavier', 'malformed-course-id')
        response = self.authenticated_get(path)
        self.assertEquals(response.status_code, 400)
