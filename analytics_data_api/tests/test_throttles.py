from unittest.mock import patch

from django.core.cache import caches
from django.test import override_settings

from analytics_data_api.throttles import ServiceUserThrottle
from analyticsdataserver.tests.utils import TestCaseWithAuthentication


class RateLimitingTests(TestCaseWithAuthentication):
    """
    Test cases for the rate limiting of analytics API calls
    """

    worker_name = 'test_worker'

    def setUp(self):
        super().setUp()
        self.path = '/docs'

    def tearDown(self):
        super().tearDown()
        caches['default'].clear()

    def _make_requests(self, num_requests, throttle_rate):
        """
        Make num_requests to an endpoint
        Return the response from the last request
        """
        with patch('rest_framework.views.APIView.throttle_classes', (ServiceUserThrottle,)):
            with patch.object(ServiceUserThrottle, 'THROTTLE_RATES', throttle_rate):
                for __ in range(num_requests - 1):
                    response = self.authenticated_get(self.path)
                    assert response.status_code == 200
                response = self.authenticated_get(self.path)
        return response

    def test_rate_limiting(self):
        response = self._make_requests(6, {'user': '5/hour'})
        assert response.status_code == 429

    @override_settings(
        ANALYTICS_API_SERVICE_USERNAMES=[worker_name],
    )
    def test_allowed_service_user(self):
        self.test_user.username = self.worker_name
        self.test_user.save()

        response = self._make_requests(5, {'service_user': '10/hour', 'user': '1/hour'})
        assert response.status_code == 200

    @override_settings(
        ANALYTICS_API_SERVICE_USERNAMES=[worker_name],
    )
    def test_denied_service_user(self):
        self.test_user.username = self.worker_name
        self.test_user.save()

        response = self._make_requests(6, {'service_user': '5/hour', 'user': '1/hour'})
        assert response.status_code == 429
