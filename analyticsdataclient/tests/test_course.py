from unittest import TestCase

from analyticsdataclient.course import Course
from analyticsdataclient.tests import InMemoryClient


class CourseTest(TestCase):

    def setUp(self):
        self.client = InMemoryClient()
        self.course = Course(self.client, 'edX/DemoX/Demo_Course')

    def test_recent_activity(self):
        # These tests don't feel terribly useful, since it's not really testing any substantial code... just that mock
        # values are returned. The risky part of the interface (the URL and the response data) is not tested at all
        # since it is mocked out.
        course_id = 'edX/DemoX/Demo_Course'
        expected_result = {
            'course_id': 'edX/DemoX/Demo_Course',
            'interval_start': '2014-05-24T00:00:00Z',
            'interval_end': '2014-06-01T00:00:00Z',
            'label': 'ACTIVE',
            'count': 300,
        }
        self.client.resources['courses/{0}/recent_activity'.format(course_id)] = expected_result

        self.assertEquals(self.course.recent_active_user_count, expected_result)
