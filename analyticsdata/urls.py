from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from analyticsdata import views

urlpatterns = patterns(
    '',
    url(r'^status$', views.status),
    url(r'^authenticated$', views.authenticated),
    url(r'^health$', views.health),

    # Course Activity
    url(r'^courses/(?P<course_id>.+)/recent_activity$', views.CourseActivityMostRecentWeekView.as_view()),

    # Answer Distribution
    url(r'^problem/(?P<usage_id>.+)/answer_distribution$', views.UsageProblemResponseAnswerDistributionView.as_view()),
)

urlpatterns = format_suffix_patterns(urlpatterns)
