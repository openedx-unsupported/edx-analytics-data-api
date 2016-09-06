import json
import StringIO
import csv

from opaque_keys.edx.keys import CourseKey
from rest_framework import status

from analytics_data_api.utils import get_filename_safe_course_id
from analytics_data_api.v0.tests.utils import flatten


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


class VerifyCsvResponseMixin(object):

    def assertCsvResponseIsValid(self, response, expected_filename, expected_data=None, expected_headers=None):

        # Validate the basic response status, content type, and filename
        self.assertEquals(response.status_code, 200)
        if expected_data:
            self.assertEquals(response['Content-Type'].split(';')[0], 'text/csv')
        self.assertEquals(response['Content-Disposition'], u'attachment; filename={}'.format(expected_filename))

        # Validate other response headers
        if expected_headers:
            for header_name, header_content in expected_headers.iteritems():
                self.assertEquals(response.get(header_name), header_content)

        # Validate the content data
        if expected_data:
            data = map(flatten, expected_data)

            # The CSV renderer sorts the headers alphabetically
            fieldnames = sorted(data[0].keys())

            # Generate the expected CSV output
            expected = StringIO.StringIO()
            writer = csv.DictWriter(expected, fieldnames)
            writer.writeheader()
            writer.writerows(data)
            self.assertEqual(response.content, expected.getvalue())
        else:
            self.assertEqual(response.content, '')

    def assertResponseFields(self, response, fields):
        content_type = response.get('Content-Type', '').split(';')[0]
        self.assertEquals(content_type, 'text/csv')

        data = StringIO.StringIO(response.content)
        reader = csv.reader(data)
        rows = []
        for row in reader:
            rows.append(row)
        # Just check the header row
        self.assertGreater(len(rows), 1)
        self.assertEqual(rows[0], fields)
