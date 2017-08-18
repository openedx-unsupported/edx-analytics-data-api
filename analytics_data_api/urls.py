from django.conf.urls import url, include
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    url(r'^v1/', include('analytics_data_api.v1.urls', 'v1')),
]

urlpatterns = format_suffix_patterns(urlpatterns)
