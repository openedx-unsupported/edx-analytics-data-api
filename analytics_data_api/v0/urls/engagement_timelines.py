from django.conf.urls import patterns, url

from analytics_data_api.v0.views import engagement_timelines as views
from analytics_data_api.v0.urls import USERNAME_PATTERN


urlpatterns = patterns(
    '',
    url(r'^{}/$'.format(USERNAME_PATTERN), views.EngagementTimelineView.as_view(), name='engagement_timelines'),
)
