from django.conf.urls import url

from analytics_data_api.constants.learner import UUID_REGEX_PATTERN
from analytics_data_api.v0.views import learners as views

app_name = 'learners'

USERNAME_PATTERN = r'(?P<username>[\w.+-]+)'

urlpatterns = [
    url(fr'^enterprise/(?P<enterprise_customer>{UUID_REGEX_PATTERN})/engagements/$',
        views.EnterpriseLearnerEngagementView.as_view(), name='engagements'),
]
