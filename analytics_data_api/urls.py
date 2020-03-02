from __future__ import absolute_import

from django.conf.urls import include, url
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    url(r'^v0/', include('analytics_data_api.v0.urls', 'v0')),
]

urlpatterns = format_suffix_patterns(urlpatterns)
