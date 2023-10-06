from django.contrib import admin
from django.urls import include, re_path
from django.views.generic import RedirectView
from edx_api_doc_tools import make_api_info, make_docs_ui_view
from rest_framework.authtoken.views import obtain_auth_token

from analyticsdataserver import views

admin.site.site_header = 'Analytics Data API Service Administration'
admin.site.site_title = admin.site.site_header

urlpatterns = [
    re_path(r'^api-auth/', include('rest_framework.urls', 'rest_framework')),
    re_path(r'^api-token-auth/', obtain_auth_token),

    re_path(r'^api/', include('analytics_data_api.urls')),
    re_path(r'^status/$', views.StatusView.as_view(), name='status'),
    re_path(r'^authenticated/$', views.AuthenticationTestView.as_view(), name='authenticated'),
    re_path(r'^health/$', views.HealthView.as_view(), name='health'),
]

urlpatterns.append(re_path(r'', include('enterprise_data.urls')))

api_ui_view = make_docs_ui_view(
    api_info=make_api_info(
        title="edX Analytics Data API",
        version="v0",
        email="program-cosmonauts@edx.org"
    ),
    api_url_patterns=urlpatterns
)

urlpatterns += [
    re_path(r'^docs/$', api_ui_view, name='api-docs'),
    re_path(r'^$', RedirectView.as_view(url='/docs')),  # pylint: disable=no-value-for-parameter
]

handler500 = 'analyticsdataserver.views.handle_internal_server_error'  # pylint: disable=invalid-name
handler404 = 'analyticsdataserver.views.handle_missing_resource_error'  # pylint: disable=invalid-name
