import json
import unittest.mock as mock

import responses
from django.test import TestCase
from requests.exceptions import ConnectionError as RequestsConnectionError

from analyticsdataserver.clients import CourseBlocksApiClient


class ClientTests(TestCase):
    @mock.patch('analyticsdataserver.clients.EdxRestApiClient')
    def setUp(self, restApiClientMock):
        self.client = CourseBlocksApiClient('http://example.com/', 'token', 5)

    @responses.activate
    def test_all_videos(self):
        responses.add(responses.GET, 'http://example.com/blocks/', body=json.dumps({'blocks': {
            'block-v1:edX+DemoX+Demo_Course+type@video+block@5c90cffecd9b48b188cbfea176bf7fe9': {
                'id': 'block-v1:edX+DemoX+Demo_Course+type@video+block@5c90cffecd9b48b188cbfea176bf7fe9'
            },
            'block-v1:edX+DemoX+Demo_Course+type@video+block@7e9b434e6de3435ab99bd3fb25bde807': {
                'id': 'block-v1:edX+DemoX+Demo_Course+type@video+block@7e9b434e6de3435ab99bd3fb25bde807'
            }
        }}), status=200, content_type='application/json')
        videos = self.client.all_videos('course_id')
        self.assertListEqual(videos, [
            {
                'video_id': 'course_id|5c90cffecd9b48b188cbfea176bf7fe9',
                'video_module_id': '5c90cffecd9b48b188cbfea176bf7fe9'
            },
            {
                'video_id': 'course_id|7e9b434e6de3435ab99bd3fb25bde807',
                'video_module_id': '7e9b434e6de3435ab99bd3fb25bde807'
            }
        ])

    @responses.activate
    @mock.patch('analyticsdataserver.clients.logger')
    def test_all_videos_401(self, logger):
        responses.add(responses.GET, 'http://example.com/blocks/', status=401, content_type='application/json')
        videos = self.client.all_videos('course_id')
        logger.warning.assert_called_with(
            'Course Blocks API failed to return video ids (%s). '
            'See README for instructions on how to authenticate the API with your local LMS.', 401)
        self.assertEqual(videos, None)

    @responses.activate
    @mock.patch('analyticsdataserver.clients.logger')
    def test_all_videos_404(self, logger):
        responses.add(responses.GET, 'http://example.com/blocks/', status=404, content_type='application/json')
        videos = self.client.all_videos('course_id')
        logger.warning.assert_called_with('Course Blocks API failed to return video ids (%s). '
                                          'Does the course exist in the LMS?', 404)
        self.assertEqual(videos, None)

    @responses.activate
    @mock.patch('analyticsdataserver.clients.logger')
    def test_all_videos_500(self, logger):
        responses.add(responses.GET, 'http://example.com/blocks/', status=418, content_type='application/json')
        videos = self.client.all_videos('course_id')
        logger.warning.assert_called_with('Course Blocks API failed to return video ids (%s).', 418)
        self.assertEqual(videos, None)

    @responses.activate
    @mock.patch('analyticsdataserver.clients.logger')
    def test_all_videos_connection_error(self, logger):
        exception = RequestsConnectionError('LMS is dead')
        responses.add(responses.GET, 'http://example.com/blocks/', body=exception)
        videos = self.client.all_videos('course_id')
        logger.warning.assert_called_with('Course Blocks API request failed. Is the LMS running?: %s', str(exception))
        self.assertEqual(videos, None)

    @responses.activate
    def test_all_videos_pass_through_bad_id(self):
        responses.add(responses.GET, 'http://example.com/blocks/', body=json.dumps({'blocks': {
            'block-v1:edX+DemoX+Demo_Course+type@video+block@5c90cffecd9b48b188cbfea176bf7fe9': {
                'id': 'bad_key'
            },
            'block-v1:edX+DemoX+Demo_Course+type@video+block@7e9b434e6de3435ab99bd3fb25bde807': {
                'id': 'bad_key'
            }
        }}), status=200, content_type='application/json')
        responses.add(responses.GET, 'http://example.com/blocks/', status=200, content_type='application/json')
        videos = self.client.all_videos('course_id')
        self.assertListEqual(videos, [
            {
                'video_id': 'course_id|bad_key',
                'video_module_id': 'bad_key'
            },
            {
                'video_id': 'course_id|bad_key',
                'video_module_id': 'bad_key'
            }
        ])
