import unittest.mock as mock

import ddt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from analytics_data_api.v0.models import CourseEnrollmentDaily
from analyticsdataserver.router import AnalyticsAPIRouter, AnalyticsDevelopmentRouter, AnalyticsModelsRouter


class AnalyticsAPIRouterTests(TestCase):
    def setUp(self):
        self.router = AnalyticsAPIRouter()

    @mock.patch.dict('analytics_data_api.middleware.thread_data.__dict__', {'analyticsapi_database': 'test'})
    def test_db_for_read_analytics_app_thread_data_with_data(self):
        self.assertEqual(self.router.db_for_read(CourseEnrollmentDaily), 'test')

    def test_db_for_read_analytics_app_thread_data_without_data(self):
        self.assertEqual(self.router.db_for_read(CourseEnrollmentDaily), getattr(settings, 'ANALYTICS_DATABASE', 'analytics'))

    @mock.patch.dict('analytics_data_api.middleware.thread_data.__dict__', {'analyticsapi_database': 'test'})
    def test_db_for_read_analytics_app_thread_data_with_data(self):
        self.assertEqual(self.router.db_for_read(get_user_model()), None)

    def test_db_for_read_not_analytics_app_thread_data_without_data(self):
        self.assertEqual(self.router.db_for_read(get_user_model()), None)


class AnalyticsModelsRouterTests(TestCase):
    def setUp(self):
        self.router = AnalyticsModelsRouter()
        self.analytics_database_slug = getattr(settings, 'ANALYTICS_DATABASE', 'analytics')

    def test_db_for_read_analytics_app(self):
        self.assertEqual(self.router.db_for_read(CourseEnrollmentDaily), self.analytics_database_slug)

    @override_settings()
    def test_db_for_read_analytics_app_no_setting(self):
        del settings.ANALYTICS_DATABASE
        self.assertEqual(self.router.db_for_read(CourseEnrollmentDaily), 'default')

    def test_db_for_read_not_analytics_app(self):
        self.assertEqual(self.router.db_for_read(get_user_model()), None)

    def test_db_for_write_analytics_app(self):
        self.assertEqual(self.router.db_for_write(CourseEnrollmentDaily), self.analytics_database_slug)

    @override_settings()
    def test_db_for_write_analytics_app_no_setting(self):
        del settings.ANALYTICS_DATABASE
        self.assertEqual(self.router.db_for_write(CourseEnrollmentDaily), 'default')

    def test_db_for_write_not_analytics_app(self):
        self.assertEqual(self.router.db_for_write(get_user_model()), None)

    def test_allow_migrate_not_analytics_app(self):
        self.assertEqual(self.router.allow_migrate(self.analytics_database_slug, get_user_model()._meta.app_label), None)


@ddt.ddt
class AnalyticsDevelopmentRouterTests(TestCase):
    """"
    Note that it's not currently possible to test the case where the default database is the only configured database.
    Databases are configured during Django internal initialization, which means modifying the DATABASES Django setting
    from a test will not work as expected.
    The Django docs explicitly caution against doing this: "We do not recommend altering the DATABASES setting."
    Please see here: https://docs.djangoproject.com/en/3.2/topics/testing/tools/#overriding-settings.
    For this reason, coverage is incomplete.
    """
    def setUp(self):
        self.router = AnalyticsDevelopmentRouter()

    @ddt.data(
        ('default', True),
        (getattr(settings, 'ANALYTICS_DATABASE', 'analytics'), True),
        (getattr(settings, 'ANALYTICS_DATABASE_V1', 'analytics_v1'), False),
    )
    @ddt.unpack
    def test_allow_migrate_not_analytics_app(self, database, expected_allow_migrate):
        self.assertEqual(self.router.allow_migrate(database, 'auth'), expected_allow_migrate)

    @ddt.data(
        (getattr(settings, 'ANALYTICS_DATABASE_V1', 'analytics_v1'), 'enterprise_data', False),
        (getattr(settings, 'default', 'default'), 'v0', False),
        (getattr(settings, 'ANALYTICS_DATABASE', 'analytics'), 'v0', True),
        (getattr(settings, 'ANALYTICS_DATABASE_V1', 'analytics_v1'), 'v0', True),
    )
    @ddt.unpack
    def test_allow_migrate_analytics_app_multiple_dbs(self, database, app_label, expected_allow_migrate):
        self.assertEqual(self.router.allow_migrate(database, app_label), expected_allow_migrate)
