from django.urls import include, path
from rest_framework.urlpatterns import format_suffix_patterns

app_name = 'analytics_data_api'

urlpatterns = [
    path('v0/', include('analytics_data_api.v0.urls')),
    path('v1/', include('analytics_data_api.v1.urls')),
]

urlpatterns = format_suffix_patterns(urlpatterns)
