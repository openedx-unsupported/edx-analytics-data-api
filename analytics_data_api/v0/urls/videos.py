import re

from django.urls import re_path

from analytics_data_api.v0.views import videos as views

app_name = 'videos'

VIDEO_URLS = [
    ('timeline', views.VideoTimelineView, 'timeline'),
]

urlpatterns = []

for path, view, name in VIDEO_URLS:
    urlpatterns.append(re_path(r'^(?P<video_id>.+)/' + re.escape(path) + r'/$', view.as_view(), name=name))
