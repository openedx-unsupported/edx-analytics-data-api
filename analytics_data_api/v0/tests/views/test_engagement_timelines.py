import datetime
import json

import ddt

from django.utils.http import urlquote
from django_dynamic_fixture import G
import pytz
from rest_framework import status

from analyticsdataserver.tests import TestCaseWithAuthentication
from analytics_data_api.constants.engagement_events import (ATTEMPTED, COMPLETED, CONTRIBUTED, DISCUSSION,
                                                            PROBLEM, VIDEO, VIEWED)
from analytics_data_api.v0 import models
from analytics_data_api.v0.tests.views import DemoCourseMixin, VerifyCourseIdMixin


@ddt.ddt
class EngagementTimelineTests(DemoCourseMixin, VerifyCourseIdMixin, TestCaseWithAuthentication):
    DEFAULT_USERNAME = 'ed_xavier'
    path_template = '/api/v0/engagement_timelines/{}/?course_id={}'

    def create_engagement(self, entity_type, event_type, entity_id, count, date=None):
        """Create a ModuleEngagement model"""
        if date is None:
            date = datetime.datetime(2015, 1, 1, tzinfo=pytz.utc)
        G(
            models.ModuleEngagement,
            course_id=self.course_id,
            username=self.DEFAULT_USERNAME,
            date=date,
            entity_type=entity_type,
            entity_id=entity_id,
            event=event_type,
            count=count,
        )

    @ddt.data(
        (PROBLEM, ATTEMPTED, 'problems_attempted', True),
        (PROBLEM, COMPLETED, 'problems_completed', True),
        (VIDEO, VIEWED, 'videos_viewed', True),
        (DISCUSSION, CONTRIBUTED, 'discussion_contributions', False),
    )
    @ddt.unpack
    def test_metric_aggregation(self, entity_type, event_type, metric_display_name, expect_id_aggregation):
        """
        Verify that some metrics are counted by unique ID, while some are
        counted by total interactions.
        """
        self.create_engagement(entity_type, event_type, 'entity-id', count=5)
        self.create_engagement(entity_type, event_type, 'entity-id', count=5)
        expected_data = {
            'days': [
                {
                    'date': '2015-01-01',
                    'discussion_contributions': 0,
                    'problems_attempted': 0,
                    'problems_completed': 0,
                    'videos_viewed': 0,
                }
            ]
        }
        if expect_id_aggregation:
            expected_data['days'][0][metric_display_name] = 1
        else:
            expected_data['days'][0][metric_display_name] = 10
        path = self.path_template.format(self.DEFAULT_USERNAME, urlquote(self.course_id))
        response = self.authenticated_get(path)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(
            response.data,
            expected_data
        )

    def test_timeline(self):
        """
        Smoke test the learner engagement timeline.
        """
        path = self.path_template.format(self.DEFAULT_USERNAME, urlquote(self.course_id))
        day_one = datetime.datetime(2015, 1, 1, tzinfo=pytz.utc)
        day_two = datetime.datetime(2015, 1, 2, tzinfo=pytz.utc)
        self.create_engagement(PROBLEM, ATTEMPTED, 'id-1', count=100, date=day_one)
        self.create_engagement(PROBLEM, COMPLETED, 'id-2', count=12, date=day_one)
        self.create_engagement(DISCUSSION, CONTRIBUTED, 'id-3', count=6, date=day_one)
        self.create_engagement(DISCUSSION, CONTRIBUTED, 'id-4', count=10, date=day_two)
        self.create_engagement(VIDEO, VIEWED, 'id-5', count=44, date=day_two)
        self.create_engagement(PROBLEM, ATTEMPTED, 'id-6', count=8, date=day_two)
        self.create_engagement(PROBLEM, ATTEMPTED, 'id-7', count=4, date=day_two)
        response = self.authenticated_get(path)
        self.assertEquals(response.status_code, 200)
        expected = {
            'days': [
                {
                    'date': '2015-01-01',
                    'discussion_contributions': 6,
                    'problems_attempted': 1,
                    'problems_completed': 1,
                    'videos_viewed': 0
                },
                {
                    'date': '2015-01-02',
                    'discussion_contributions': 10,
                    'problems_attempted': 2,
                    'problems_completed': 0,
                    'videos_viewed': 1
                },
            ]
        }
        self.assertEquals(response.data, expected)

    def test_day_gap(self):
        path = self.path_template.format(self.DEFAULT_USERNAME, urlquote(self.course_id))
        first_day = datetime.datetime(2015, 5, 26, tzinfo=pytz.utc)
        last_day = datetime.datetime(2015, 5, 28, tzinfo=pytz.utc)
        self.create_engagement(VIDEO, VIEWED, 'id-1', count=1, date=first_day)
        self.create_engagement(PROBLEM, ATTEMPTED, entity_id='id-2', count=1, date=last_day)
        response = self.authenticated_get(path)
        self.assertEquals(response.status_code, 200)
        expected = {
            'days': [
                {
                    'date': '2015-05-26',
                    'discussion_contributions': 0,
                    'problems_attempted': 0,
                    'problems_completed': 0,
                    'videos_viewed': 1
                },
                {
                    'date': '2015-05-27',
                    'discussion_contributions': 0,
                    'problems_attempted': 0,
                    'problems_completed': 0,
                    'videos_viewed': 0
                },
                {
                    'date': '2015-05-28',
                    'discussion_contributions': 0,
                    'problems_attempted': 1,
                    'problems_completed': 0,
                    'videos_viewed': 0
                },
            ]
        }
        self.assertEquals(response.data, expected)

    def test_not_found(self):
        path = self.path_template.format(self.DEFAULT_USERNAME, urlquote(self.course_id))
        response = self.authenticated_get(path)
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)
        expected = {
            u"error_code": u"no_learner_engagement_timeline",
            u"developer_message": u"Learner {} engagement timeline not found for course {}.".format(
                self.DEFAULT_USERNAME, self.course_id)
        }
        self.assertDictEqual(json.loads(response.content), expected)

    def test_no_course_id(self):
        base_path = '/api/v0/engagement_timelines/{}'
        response = self.authenticated_get((base_path).format('ed_xavier'))
        self.verify_no_course_id(response)

    def test_bad_course_id(self):
        path = self.path_template.format(self.DEFAULT_USERNAME, 'malformed-course-id')
        response = self.authenticated_get(path)
        self.verify_bad_course_id(response)
