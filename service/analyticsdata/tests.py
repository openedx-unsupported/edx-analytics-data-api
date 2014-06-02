
from django.contrib.auth.models import User
from django.db.utils import ConnectionHandler
from django.test import TestCase
from mock import patch
from rest_framework.authtoken.models import Token

from analyticsdata import views


# NOTE: Full URLs are used throughout these tests to ensure that the API contract is fulfilled. The URLs should *not*
# change for versions greater than 1.0.0. Tests target a specific version of the API, additional tests should be added
# for subsequent versions if there are breaking changes introduced in those versions.


class OperationalEndpointsTest(TestCase):

    def test_status(self):
        response = self.client.get('/api/v0/status')
        self.assertEquals(response.status_code, 200)

    def test_authentication_check_failure(self):
        response = self.client.get('/api/v0/authenticated')
        self.assertEquals(response.status_code, 401)

    def test_authentication_check_success(self):
        test_user = User.objects.create_user('tester', 'test@example.com', 'testpassword')
        token = Token.objects.create(user=test_user)
        response = self.client.get('/api/v0/authenticated', HTTP_AUTHORIZATION='Token ' + token.key)
        self.assertEquals(response.status_code, 200)

    def test_health(self):
        response = self.client.get('/api/v0/health')
        self.assertEquals(
            response.data,
            {
                'overall_status': 'OK',
                'detailed_status': {
                    'database_connections': {
                        'default': 'OK'
                    }
                }
            }
        )
        self.assertEquals(response.status_code, 200)

    def test_database_down(self):
        databases = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:"
            },
            "reporting": {}
        }
        with patch('analyticsdata.views.connections', ConnectionHandler(databases)):
            response = self.client.get('/api/v0/health')
            self.assertEquals(
                response.data,
                {
                    'overall_status': 'UNAVAILABLE',
                    'detailed_status': {
                        'database_connections': {
                            'default': 'OK',
                            'reporting': 'UNAVAILABLE'
                        }
                    }
                }
            )
            self.assertEquals(response.status_code, 200)
