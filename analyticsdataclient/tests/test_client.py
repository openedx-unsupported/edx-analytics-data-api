import json
from unittest import TestCase

import httpretty

from analyticsdataclient.client import RestClient, ClientError


class RestClientTest(TestCase):

    BASE_URI = 'http://localhost:9091'
    VERSIONED_BASE_URI = BASE_URI + '/api/v0'

    TEST_ENDPOINT = 'test'
    TEST_URI = VERSIONED_BASE_URI + '/' + TEST_ENDPOINT

    def setUp(self):
        httpretty.enable()
        self.client = RestClient(base_url=self.BASE_URI)

    def tearDown(self):
        httpretty.disable()

    def test_has_resource(self):
        httpretty.register_uri(httpretty.GET, self.TEST_URI, body='')
        self.assertEquals(self.client.has_resource(self.TEST_ENDPOINT), True)

    def test_missing_resource(self):
        httpretty.register_uri(httpretty.GET, self.TEST_URI, body='', status=404)
        self.assertEquals(self.client.has_resource(self.TEST_ENDPOINT), False)

    def test_failed_authentication(self):
        self.client = RestClient(base_url=self.BASE_URI, auth_token='atoken')
        httpretty.register_uri(httpretty.GET, self.TEST_URI, body='', status=401)

        self.assertEquals(self.client.has_resource(self.TEST_ENDPOINT), False)
        self.assertEquals(httpretty.last_request().headers['Authorization'], 'Token atoken')

    def test_get(self):
        data = {
            'foo': 'bar'
        }
        httpretty.register_uri(httpretty.GET, self.TEST_URI, body=json.dumps(data))
        self.assertEquals(self.client.get(self.TEST_ENDPOINT), data)

    def test_get_invalid_json(self):
        data = {
            'foo': 'bar'
        }
        httpretty.register_uri(httpretty.GET, self.TEST_URI, body=json.dumps(data)[:6])
        with self.assertRaises(ClientError):
            self.client.get(self.TEST_ENDPOINT)
