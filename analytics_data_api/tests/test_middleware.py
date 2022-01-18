from unittest import mock

from django.conf import settings
from django.test import override_settings

from analytics_data_api.middleware import thread_data
from analytics_data_api.tests.test_utils import set_databases
from analytics_data_api.v0.tests.views import CourseSamples
from analyticsdataserver.tests.utils import TestCaseWithAuthentication


@set_databases
class RequestVersionMiddleware(TestCaseWithAuthentication):
    def test_request_version_middleware_v1(self):
        # Because the AnalyticsModelsRouter prevents migrations from running on the ANALYTICS_DATABASE_V1
        # database, and the AnalyticsDevelopmentRouter is not configured to be used in the test environment,
        # the analytics tables don't exist in the ANALYTICS_DATABASE_V1 database. This causes errors like
        # "django.db.utils.OperationalError: no such table: course_activity" to be thrown when the
        # CourseActivityWeeklyView view is run. Therefore, we mock out the get_queryset method, because all we care
        # about is the middleware correctly setting the analyticsapi_database attribute of the thread local data
        # correctly.
        with mock.patch('analytics_data_api.v0.views.courses.CourseActivityWeeklyView.get_queryset') as qs:
            qs.return_value = None
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
