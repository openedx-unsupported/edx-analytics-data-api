from unittest import TestCase

from analyticsdataclient.client import Client, ClientError
from analyticsdataclient.status import Status


class StatusTest(TestCase):

    def setUp(self):
        self.client = InMemoryClient()
        self.status = Status(self.client)

    def test_alive(self):
        self.assertEquals(self.status.alive, False)

        self.client.resources['status'] = ''
        self.assertEquals(self.status.alive, True)

    def test_authenticated(self):
        self.assertEquals(self.status.authenticated, False)

        self.client.resources['authenticated'] = ''
        self.assertEquals(self.status.authenticated, True)

    def test_healthy(self):
        self.client.resources['health'] = {
            'overall_status': 'OK',
            'detailed_status': {
                'database_connection': 'OK'
            }
        }

        self.assertEquals(self.status.healthy, True)

    def test_not_healthy(self):
        self.client.resources['health'] = {
            'overall_status': 'UNAVAILABLE',
            'detailed_status': {
                'database_connection': 'UNAVAILABLE'
            }
        }

        self.assertEquals(self.status.healthy, False)

    def test_invalid_health_value(self):
        self.client.resources['health'] = {}

        self.assertEquals(self.status.healthy, False)


class InMemoryClient(Client):

    def __init__(self):
        super(InMemoryClient, self).__init__()
        self.resources = {}

    def has_resource(self, resource, timeout=None):
        try:
            self.get(resource, timeout=timeout)
            return True
        except ClientError:
            return False

    def get(self, resource, timeout=None):
        try:
            return self.resources[resource]
        except KeyError:
            raise ClientError('Unable to find requested resource')
