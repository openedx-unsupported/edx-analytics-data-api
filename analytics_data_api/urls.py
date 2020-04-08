

from django.conf.urls import include, url
from rest_framework.urlpatterns import format_suffix_patterns

app_name = 'analytics_data_api'

urlpatterns = [
    url(r'^v0/', include('analytics_data_api.v0.urls')),
]

urlpatterns = format_suffix_patterns(urlpatterns)
