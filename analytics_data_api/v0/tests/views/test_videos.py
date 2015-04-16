import datetime

from django.conf import settings
from django_dynamic_fixture import G

from analytics_data_api.v0 import models
from analyticsdataserver.tests import TestCaseWithAuthentication


class VideoTimelineTests(TestCaseWithAuthentication):

    def _get_data(self, video_id=None):
        return self.authenticated_get('/api/v0/videos/{}/timeline'.format(video_id))

    def test_get(self):
        # add a blank row, which shouldn't be included in results
        G(models.VideoTimeline)

        video_id = 'v1d30'
        created = datetime.datetime.utcnow()
        date_time_format = '%Y-%m-%d %H:%M:%S'
        G(models.VideoTimeline, pipeline_video_id=video_id, segment=0, num_users=10,
          num_views=50, created=created.strftime(date_time_format))
        G(models.VideoTimeline, pipeline_video_id=video_id, segment=1, num_users=1,
          num_views=1234, created=created.strftime(date_time_format))

        alt_video_id = 'altv1d30'
        alt_created = created + datetime.timedelta(seconds=17)
        G(models.VideoTimeline, pipeline_video_id=alt_video_id, segment=0, num_users=10231,
          num_views=834828, created=alt_created.strftime(date_time_format))

        expected = [
            {
                'segment': 0,
                'num_users': 10,
                'num_views': 50,
                'created': created.strftime(settings.DATETIME_FORMAT)
            },
            {
                'segment': 1,
                'num_users': 1,
                'num_views': 1234,
                'created': created.strftime(settings.DATETIME_FORMAT)
            }
        ]
        response = self._get_data(video_id)
        self.assertEquals(response.status_code, 200)
        self.assertListEqual(response.data, expected)

        expected = [
            {
                'segment': 0,
                'num_users': 10231,
                'num_views': 834828,
                'created': alt_created.strftime(settings.DATETIME_FORMAT)
            }
        ]
        response = self._get_data(alt_video_id)
        self.assertEquals(response.status_code, 200)
        self.assertListEqual(response.data, expected)

    def test_get_404(self):
        response = self._get_data('no_id')
        self.assertEquals(response.status_code, 404)
