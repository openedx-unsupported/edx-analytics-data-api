from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from analyticsdata import views

urlpatterns = patterns(
    '',
    url(r'^status$', views.status),
    url(r'^authenticated$', views.authenticated),
    url(r'^health$', views.health),

    # User Activity
    url(r'^courses/(?P<course_id>.+)/user_activity/?$', views.CourseUserActivityListView.as_view()),
    url(r'^user_activity/?$', views.CourseUserActivityListView.as_view()),
    url(r'^user_activity/(?P<pk>[0-9]+)', views.CourseUserActivityView.as_view(), name='courseuseractivitybyweek-detail'),
)

urlpatterns = format_suffix_patterns(urlpatterns)
