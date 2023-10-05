from django.urls import include, re_path
from rest_framework.urlpatterns import format_suffix_patterns

app_name = 'analytics_data_api'

urlpatterns = [
    re_path(r'^v0/', include('analytics_data_api.v0.urls')),
    re_path(r'^v1/', include('analytics_data_api.v1.urls')),
]

urlpatterns = format_suffix_patterns(urlpatterns)
