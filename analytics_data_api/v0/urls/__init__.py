from django.conf.urls import patterns, url, include
from analytics_data_api.v0.views import operational

urlpatterns = patterns(
    '',
    url(r'^status$', operational.StatusView.as_view()),
    url(r'^authenticated$', operational.AuthenticationTestView.as_view()),
    url(r'^health$', operational.HealthView.as_view()),

    url(r'^courses/', include('analytics_data_api.v0.urls.courses', namespace='courses')),
)
