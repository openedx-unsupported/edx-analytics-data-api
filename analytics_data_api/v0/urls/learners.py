

from django.conf.urls import url

from analytics_data_api.v0.urls import COURSE_ID_PATTERN
from analytics_data_api.v0.views import learners as views

from analytics_data_api.constants.learner import UUID_REGEX_PATTERN

app_name = 'learners'

USERNAME_PATTERN = r'(?P<username>[\w.+-]+)'

urlpatterns = [
    url(r'^learners/$', views.LearnerListView.as_view(), name='learners'),
    url(r'^learners/{}/$'.format(USERNAME_PATTERN), views.LearnerView.as_view(), name='learner'),
    url(r'^engagement_timelines/{}/$'.format(USERNAME_PATTERN),
        views.EngagementTimelineView.as_view(), name='engagement_timelines'),
    url(r'^course_learner_metadata/{}/$'.format(COURSE_ID_PATTERN),
        views.CourseLearnerMetadata.as_view(), name='course_learner_metadata'),
    url(r'^enterprise/(?P<enterprise_customer>{})/engagements/$'.format(UUID_REGEX_PATTERN),
        views.EnterpriseLearnerEngagementView.as_view(), name='engagements'),
]
