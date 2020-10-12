from django.conf.urls import url

from analytics_data_api.constants.learner import UUID_REGEX_PATTERN
from analytics_data_api.v0.urls import COURSE_ID_PATTERN
from analytics_data_api.v0.views import learners as views

app_name = 'learners'

USERNAME_PATTERN = r'(?P<username>[\w.+-]+)'

urlpatterns = [
    url(r'^learners/$', views.LearnerListView.as_view(), name='learners'),
    url(fr'^learners/{USERNAME_PATTERN}/$', views.LearnerView.as_view(), name='learner'),
    url(fr'^engagement_timelines/{USERNAME_PATTERN}/$',
        views.EngagementTimelineView.as_view(), name='engagement_timelines'),
    url(fr'^course_learner_metadata/{COURSE_ID_PATTERN}/$',
        views.CourseLearnerMetadata.as_view(), name='course_learner_metadata'),
    url(fr'^enterprise/(?P<enterprise_customer>{UUID_REGEX_PATTERN})/engagements/$',
        views.EnterpriseLearnerEngagementView.as_view(), name='engagements'),
]
