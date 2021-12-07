import logging
import unittest.mock as mock

from django.contrib.auth.models import User
from django.test import TestCase

from analytics_data_api.v0.models import CourseEnrollmentByBirthYear, CourseEnrollmentDaily
from analyticsdataserver.router import AnalyticsApiRouter


class AnalyticsApiRouterTests(TestCase):
    def setUp(self):
        self.router = AnalyticsApiRouter()

    def test_allow_relation(self):
        """
        Relations should only be allowed for objects contained within the same database.
        """
        self.assertFalse(self.router.allow_relation(CourseEnrollmentDaily, User))
        self.assertTrue(self.router.allow_relation(CourseEnrollmentDaily, CourseEnrollmentByBirthYear))

    @mock.patch.dict('analytics_data_api.middleware.thread_data.__dict__', {'analyticsapi_database': 'test'})
    def test_db_for_read_thread_data_with_data(self):
        self.assertEqual(self.router.db_for_read(CourseEnrollmentDaily), 'test')

    def test_db_for_read_thread_data_without_data(self):
        self.assertEqual(self.router.db_for_read(CourseEnrollmentDaily), 'default')
