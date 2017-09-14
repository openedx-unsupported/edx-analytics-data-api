import csv
import json
import StringIO
from collections import OrderedDict
from urllib import urlencode

from django_dynamic_fixture import G
from rest_framework import status

from analytics_data_api.v0.tests.utils import flatten


class CourseSamples(object):

    course_ids = [
        'edX/DemoX/Demo_Course',
        'course-v1:edX+DemoX+Demo_2014',
        'ccx-v1:edx+1.005x-CCX+rerun+ccx@15'
    ]

    program_ids = [
        '482dee71-e4b9-4b42-a47b-3e16bb69e8f2',
        '71c14f59-35d5-41f2-a017-e108d2d9f127',
        'cfc6b5ee-6aa1-4c82-8421-20418c492618'
    ]


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


class APIListViewTestMixin(object):
    model = None
    model_id = 'id'
    ids_param = 'ids'
    serializer = None
    expected_results = []
    list_name = 'list'
    default_ids = []
    always_exclude = ['created']
    test_post_method = False

    def path(self, query_data=None):
        query_data = query_data or {}
        concat_query_data = {param: ','.join(arg) for param, arg in query_data.items() if arg}
        query_string = '?{}'.format(urlencode(concat_query_data)) if concat_query_data else ''
        return '/api/v0/{}/{}'.format(self.list_name, query_string)

    def validated_request(self, ids=None, fields=None, exclude=None, **extra_args):
        params = [self.ids_param, 'fields', 'exclude']
        args = [ids, fields, exclude]
        data = {param: arg for param, arg in zip(params, args) if arg}
        data.update(extra_args)

        get_response = self.authenticated_get(self.path(data))
        if self.test_post_method:
            post_response = self.authenticated_post(self.path(), data=data)
            self.assertEquals(get_response.status_code, post_response.status_code)
            if 200 <= get_response.status_code < 300:
                self.assertEquals(get_response.data, post_response.data)

        return get_response

    def create_model(self, model_id, **kwargs):
        pass  # implement in subclass

    def generate_data(self, ids=None, **kwargs):
        """Generate list data"""
        if ids is None:
            ids = self.default_ids

        for item_id in ids:
            self.create_model(item_id, **kwargs)

    def expected_result(self, item_id):
        result = OrderedDict([
            (self.model_id, item_id),
        ])
        return result

    def all_expected_results(self, ids=None, **kwargs):
        if ids is None:
            ids = self.default_ids

        return [self.expected_result(item_id, **kwargs) for item_id in ids]

    def _test_all_items(self, ids):
        self.generate_data()
        response = self.validated_request(ids=ids, exclude=self.always_exclude)
        self.assertEquals(response.status_code, 200)
        self.assertItemsEqual(response.data, self.all_expected_results(ids=ids))

    def _test_one_item(self, item_id):
        self.generate_data()
        response = self.validated_request(ids=[item_id], exclude=self.always_exclude)
        self.assertEquals(response.status_code, 200)
        self.assertItemsEqual(response.data, [self.expected_result(item_id)])

    def _test_fields(self, fields):
        self.generate_data()
        response = self.validated_request(fields=fields)
        self.assertEquals(response.status_code, 200)

        # remove fields not requested from expected results
        expected_results = self.all_expected_results()
        for expected_result in expected_results:
            for field_to_remove in set(expected_result.keys()) - set(fields):
                expected_result.pop(field_to_remove)

        self.assertItemsEqual(response.data, expected_results)

    def test_no_items(self):
        response = self.validated_request()
        self.assertEquals(response.status_code, 404)

    def test_no_matching_items(self):
        self.generate_data()
        response = self.validated_request(ids=['no/items/found'])
        self.assertEquals(response.status_code, 404)
