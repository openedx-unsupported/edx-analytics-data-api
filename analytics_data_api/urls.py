from django.conf.urls import url, include
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    url(r'^v0/', include('analytics_data_api.v0.urls', 'v0')),
]

urlpatterns = format_suffix_patterns(urlpatterns)
