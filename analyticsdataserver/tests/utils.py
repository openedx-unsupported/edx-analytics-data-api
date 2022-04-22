from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token


class TestCaseWithAuthentication(TestCase):
    def setUp(self):
        super().setUp()
        self.test_user = User.objects.create_user('tester', 'test@example.com', 'testpassword')
        self.token = Token.objects.create(user=self.test_user)

    def authenticated_get(self, path, data=None, follow=True, **extra):
        data = data or {}
        return self.client.get(
            path=path, data=data, follow=follow, HTTP_AUTHORIZATION='Token ' + self.token.key, **extra
        )

    def authenticated_post(self, path, data=None, follow=True, **extra):
        data = data or {}
        return self.client.post(
            path=path, data=data, follow=follow, HTTP_AUTHORIZATION='Token ' + self.token.key, **extra
        )
