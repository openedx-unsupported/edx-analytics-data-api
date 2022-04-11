from django.conf import settings
from django.test import override_settings

from analytics_data_api.middleware import thread_data
from analytics_data_api.tests.test_utils import set_databases
from analytics_data_api.v0.tests.views import CourseSamples
from analyticsdataserver.tests.utils import TestCaseWithAuthentication


@set_databases
class RequestVersionMiddleware(TestCaseWithAuthentication):
    def test_request_version_middleware_v1(self):
        self.authenticated_get('/api/v1/courses/{}/activity'.format(
            CourseSamples.course_ids[0]))

        self.assertEqual(thread_data.analyticsapi_database, getattr(settings, 'ANALYTICS_DATABASE_V1'))

    @override_settings(ANALYTICS_DATABASE_V1=None)
    def test_request_version_middleware_v1_no_setting(self):
        self.authenticated_get('/api/v1/courses/{}/activity'.format(
            CourseSamples.course_ids[0]))

        self.assertEqual(thread_data.analyticsapi_database, getattr(settings, 'ANALYTICS_DATABASE_V1'))

    def test_request_version_middleware_v0(self):
        self.authenticated_get('/api/v0/courses/{}/activity'.format(
            CourseSamples.course_ids[0]))

        self.assertEqual("analytics", getattr(thread_data, 'analyticsapi_database'))
