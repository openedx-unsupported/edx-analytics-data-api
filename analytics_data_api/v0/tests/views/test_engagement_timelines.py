import datetime
import json

from django.utils.http import urlquote
from django_dynamic_fixture import G
import pytz
from rest_framework import status

from analyticsdataserver.tests import TestCaseWithAuthentication
from analytics_data_api.constants import engagement_entity_types, engagement_events
from analytics_data_api.v0 import models
from analytics_data_api.v0.tests.views import DemoCourseMixin, VerifyCourseIdMixin


class EngagementTimelineTests(DemoCourseMixin, VerifyCourseIdMixin, TestCaseWithAuthentication):
    DEFAULT_USERNAME = 'ed_xavier'
    path_template = '/api/v0/engagement_timelines/{}/?course_id={}'

    def _create_engagement(self):
        """ Create module engagement data for testing. """
        G(models.ModuleEngagement, course_id=self.course_id, username=self.DEFAULT_USERNAME,
          date=datetime.datetime(2015, 1, 1, tzinfo=pytz.utc), entity_type=engagement_entity_types.PROBLEM,
          entity_id='some-type-of-id', event=engagement_events.ATTEMPTED, count=100)
        G(models.ModuleEngagement, course_id=self.course_id, username=self.DEFAULT_USERNAME,
          date=datetime.datetime(2015, 1, 1, tzinfo=pytz.utc), entity_type=engagement_entity_types.PROBLEM,
          entity_id='some-type-of-id', event=engagement_events.COMPLETED, count=12)
        G(models.ModuleEngagement, course_id=self.course_id, username=self.DEFAULT_USERNAME,
          date=datetime.datetime(2015, 1, 2, tzinfo=pytz.utc), entity_type=engagement_entity_types.DISCUSSION,
          entity_id='some-type-of-id', event=engagement_events.CONTRIBUTIONS, count=10)
        G(models.ModuleEngagement, course_id=self.course_id, username=self.DEFAULT_USERNAME,
          date=datetime.datetime(2015, 1, 2, tzinfo=pytz.utc), entity_type=engagement_entity_types.VIDEO,
          entity_id='some-type-of-id', event=engagement_events.VIEWED, count=44)
        G(models.ModuleEngagement, course_id=self.course_id, username=self.DEFAULT_USERNAME,
          date=datetime.datetime(2015, 1, 2, tzinfo=pytz.utc), entity_type=engagement_entity_types.PROBLEM,
          entity_id='some-type-of-id', event=engagement_events.ATTEMPTED, count=8)

    def test_timeline(self):
        path = self.path_template.format(self.DEFAULT_USERNAME, urlquote(self.course_id))
        self._create_engagement()
        response = self.authenticated_get(path)
        self.assertEquals(response.status_code, 200)

        expected = {
            'days': [
                {
                    'date': '2015-01-01',
                    'discussion_contributions': 0,
                    'problems_attempted': 100,
                    'problems_completed': 12,
                    'videos_viewed': 0
                },
                {
                    'date': '2015-01-02',
                    'discussion_contributions': 10,
                    'problems_attempted': 8,
                    'problems_completed': 0,
                    'videos_viewed': 44
                },
            ]
        }
        self.assertEquals(response.data, expected)

    def test_one(self):
        path = self.path_template.format(self.DEFAULT_USERNAME, urlquote(self.course_id))
        G(models.ModuleEngagement, course_id=self.course_id, username=self.DEFAULT_USERNAME,
          date=datetime.datetime(2015, 5, 28, tzinfo=pytz.utc), entity_type=engagement_entity_types.PROBLEM,
          entity_id='some-type-of-id', event=engagement_events.ATTEMPTED, count=6923)
        response = self.authenticated_get(path)
        self.assertEquals(response.status_code, 200)
        expected = {
            'days': [
                {
                    'date': '2015-05-28',
                    'discussion_contributions': 0,
                    'problems_attempted': 6923,
                    'problems_completed': 0,
                    'videos_viewed': 0
                },
            ]
        }
        self.assertEquals(response.data, expected)

    def test_day_gap(self):
        path = self.path_template.format(self.DEFAULT_USERNAME, urlquote(self.course_id))
        G(models.ModuleEngagement, course_id=self.course_id, username=self.DEFAULT_USERNAME,
          date=datetime.datetime(2015, 5, 26, tzinfo=pytz.utc), entity_type=engagement_entity_types.VIDEO,
          entity_id='some-type-of-id', event=engagement_events.VIEWED, count=1)
        G(models.ModuleEngagement, course_id=self.course_id, username=self.DEFAULT_USERNAME,
          date=datetime.datetime(2015, 5, 28, tzinfo=pytz.utc), entity_type=engagement_entity_types.PROBLEM,
          entity_id='some-type-of-id', event=engagement_events.ATTEMPTED, count=6923)
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
                    'date': '2015-05-28',
                    'discussion_contributions': 0,
                    'problems_attempted': 6923,
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
