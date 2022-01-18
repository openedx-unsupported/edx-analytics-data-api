from django.test import TestCase
from django.urls import reverse

from analytics_data_api.tests.test_utils import set_databases


@set_databases
class UrlRedirectTests(TestCase):
    api_root_path = '/api/v0/'

    def assertRedirectsToRootPath(self, path, **kwargs):
        assert_kwargs = {'status_code': 302}
        assert_kwargs.update(kwargs)

        p = f'{self.api_root_path}{path}/'
        response = self.client.get(p)
        self.assertRedirects(response, reverse(path), **assert_kwargs)

    def test_authenticated(self):
        self.assertRedirectsToRootPath('authenticated', target_status_code=401)

    def test_health(self):
        self.assertRedirectsToRootPath('health')

    def test_status(self):
        self.assertRedirectsToRootPath('status')
