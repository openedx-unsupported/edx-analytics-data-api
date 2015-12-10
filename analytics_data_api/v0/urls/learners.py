from django.conf.urls import patterns, url

from analytics_data_api.v0.views import learners as views
from analytics_data_api.v0.urls import USERNAME_PATTERN


urlpatterns = patterns(
    '',
    url(r'^$', views.LearnerListView.as_view(), name='learners'),
    url(r'^{}/$'.format(USERNAME_PATTERN), views.LearnerView.as_view(), name='learner'),
)
