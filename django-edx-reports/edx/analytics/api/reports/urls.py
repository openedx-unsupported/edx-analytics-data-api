from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from edx.analytics.api.reports import views

urlpatterns = patterns(
    '',
    url(r'^status$', views.status),
    url(r'^authenticated$', views.authenticated),
    url(r'^health$', views.health),
)

urlpatterns = format_suffix_patterns(urlpatterns)
