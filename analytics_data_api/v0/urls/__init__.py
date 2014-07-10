from django.conf.urls import patterns, url, include

urlpatterns = patterns(
    '',
    url(r'^courses/', include('analytics_data_api.v0.urls.courses', namespace='courses')),
)
