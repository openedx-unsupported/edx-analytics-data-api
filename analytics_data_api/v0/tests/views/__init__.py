import json

from opaque_keys.edx.keys import CourseKey
from rest_framework import status

from analytics_data_api.utils import get_filename_safe_course_id

DEMO_COURSE_ID = u'course-v1:edX+DemoX+Demo_2014'
SANITIZED_DEMO_COURSE_ID = get_filename_safe_course_id(DEMO_COURSE_ID)


class DemoCourseMixin(object):
    course_key = None
    course_id = None

    @classmethod
    def setUpClass(cls):
        cls.course_id = DEMO_COURSE_ID
        cls.course_key = CourseKey.from_string(cls.course_id)
        super(DemoCourseMixin, cls).setUpClass()


class VerifyCourseIdMixin(object):

    def verify_no_course_id(self, response):
        """ Assert that a course ID must be provided. """
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        expected = {
            u"error_code": u"course_not_specified",
            u"developer_message": u"Course id/key not specified."
        }
        self.assertDictEqual(json.loads(response.content), expected)

    def verify_bad_course_id(self, response, course_id='malformed-course-id'):
        """ Assert that a course ID must be valid. """
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        expected = {
            u"error_code": u"course_key_malformed",
            u"developer_message": u"Course id/key {} malformed.".format(course_id)
        }
        self.assertDictEqual(json.loads(response.content), expected)
