import re

from django.conf.urls import patterns, url

from analytics_data_api.v0.views import videos as views

VIDEO_URLS = [
    ('timeline', views.VideoTimelineView, 'timeline'),
]

urlpatterns = []

for path, view, name in VIDEO_URLS:
    urlpatterns += patterns('', url(r'^(?P<video_id>.+)/' + re.escape(path) + r'/$', view.as_view(), name=name))
