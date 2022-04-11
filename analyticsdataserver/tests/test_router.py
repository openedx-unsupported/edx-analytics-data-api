import unittest.mock as mock

import ddt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from analytics_data_api.v0.models import CourseEnrollmentDaily
from analyticsdataserver.router import AnalyticsAPIRouter, AnalyticsModelsRouter


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


@ddt.ddt
class AnalyticsModelsRouterTests(TestCase):
    def setUp(self):
        self.router = AnalyticsModelsRouter()
        self.analytics_database_slug = getattr(settings, 'ANALYTICS_DATABASE', 'analytics')

    def test_db_for_read_analytics_app(self):
        self.assertEqual(self.router.db_for_read(CourseEnrollmentDaily), self.analytics_database_slug)

    @override_settings(
        ANALYTICS_DATABASE=None,
        ANALYTICS_DATABASE_V1=None
    )
    def test_db_for_read_analytics_app_no_setting(self):
        self.assertEqual(self.router.db_for_read(CourseEnrollmentDaily), 'default')

    def test_db_for_read_not_analytics_app(self):
        self.assertEqual(self.router.db_for_read(get_user_model()), 'default')

    def test_db_for_write_analytics_app(self):
        self.assertEqual(self.router.db_for_write(CourseEnrollmentDaily), self.analytics_database_slug)

    @override_settings(
        ANALYTICS_DATABASE=None,
        ANALYTICS_DATABASE_V1=None
    )
    def test_db_for_write_analytics_app_no_setting(self):
        self.assertEqual(self.router.db_for_write(CourseEnrollmentDaily), 'default')

    def test_db_for_write_not_analytics_app(self):
        self.assertEqual(self.router.db_for_write(get_user_model()), 'default')

    @ddt.data(
        ('default', True),
        (getattr(settings, 'ANALYTICS_DATABASE', 'analytics'), False),
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

    @ddt.data(
        (getattr(settings, 'ANALYTICS_DATABASE', 'analytics'), True),
        (getattr(settings, 'ANALYTICS_DATABASE_V1', 'analytics_v1'), False),
    )
    @ddt.unpack
    @override_settings(ANALYTICS_DATABASE_V1=None)
    def test_does_not_migrate_database_with_no_env_setting(self, database, expected_allow_migrate):
        self.assertEqual(self.router.allow_migrate(database, 'v0'), expected_allow_migrate)
        self.assertEqual(self.router.allow_migrate(database, 'v1'), expected_allow_migrate)

    @ddt.data(
        (getattr(settings, 'default', 'default'), 'auth', True),
        (getattr(settings, 'default', 'default'), 'v0', True),
        (getattr(settings, 'default', 'default'), 'v1', True),
        (getattr(settings, 'ANALYTICS_DATABASE', 'analytics'), 'v0', False),
        (getattr(settings, 'ANALYTICS_DATABASE_V1', 'analytics_v1'), 'v0', False),
        (getattr(settings, 'ANALYTICS_DATABASE_V1', 'analytics_v1'), 'v1', False),
    )
    @ddt.unpack
    @override_settings(
        ANALYTICS_DATABASE=None,
        ANALYTICS_DATABASE_V1=None
    )
    def test_migrate_single_database_environment(self, database, app_label, expected_allow_migrate):
        self.assertEqual(self.router.allow_migrate(database, app_label), expected_allow_migrate)
