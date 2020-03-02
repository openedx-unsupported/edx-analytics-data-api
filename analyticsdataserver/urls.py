from __future__ import absolute_import

from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import RedirectView
from rest_framework.authtoken.views import obtain_auth_token

from analyticsdataserver import views

admin.site.site_header = 'Analytics Data API Service Administration'
admin.site.site_title = admin.site.site_header

urlpatterns = [
    url(r'^$', RedirectView.as_view(url='/docs')),  # pylint: disable=no-value-for-parameter

    url(r'^api-auth/', include('rest_framework.urls', 'rest_framework')),
    url(r'^api-token-auth/', obtain_auth_token),

    url(r'^api/', include('analytics_data_api.urls', 'api')),
    url(r'^docs/', views.SwaggerSchemaView.as_view()),

    url(r'^status/$', views.StatusView.as_view(), name='status'),
    url(r'^authenticated/$', views.AuthenticationTestView.as_view(), name='authenticated'),
    url(r'^health/$', views.HealthView.as_view(), name='health'),
]

urlpatterns.append(url(r'', include('enterprise_data.urls')))

handler500 = 'analyticsdataserver.views.handle_internal_server_error'  # pylint: disable=invalid-name
handler404 = 'analyticsdataserver.views.handle_missing_resource_error'  # pylint: disable=invalid-name
