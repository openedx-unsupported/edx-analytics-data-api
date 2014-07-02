from django.conf.urls import patterns, url, include
from analytics_data_api.v0 import views

urlpatterns = patterns(
    '',
    url(r'^status$', views.status),
    url(r'^authenticated$', views.authenticated),
    url(r'^health$', views.health),

    url(r'^courses/', include('analytics_data_api.v0.urls.courses', namespace='courses')),
)
