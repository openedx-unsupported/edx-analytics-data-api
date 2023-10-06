from django.contrib import admin
from django.urls import path
from django.urls import include, re_path
from django.views.generic import RedirectView
from edx_api_doc_tools import make_api_info, make_docs_ui_view
from rest_framework.authtoken.views import obtain_auth_token

from analyticsdataserver import views

admin.site.site_header = 'Analytics Data API Service Administration'
admin.site.site_title = admin.site.site_header

urlpatterns = [
    path('api-auth/', include('rest_framework.urls', 'rest_framework')),
    re_path(r'^api-token-auth/', obtain_auth_token),

    path('api/', include('analytics_data_api.urls')),
    path('status/', views.StatusView.as_view(), name='status'),
    path('authenticated/', views.AuthenticationTestView.as_view(), name='authenticated'),
    path('health/', views.HealthView.as_view(), name='health'),
]

urlpatterns.append(path('', include('enterprise_data.urls')))

api_ui_view = make_docs_ui_view(
    api_info=make_api_info(
        title="edX Analytics Data API",
        version="v0",
        email="program-cosmonauts@edx.org"
    ),
    api_url_patterns=urlpatterns
)

urlpatterns += [
    path('docs/', api_ui_view, name='api-docs'),
    path('', RedirectView.as_view(url='/docs')),  # pylint: disable=no-value-for-parameter
]

handler500 = 'analyticsdataserver.views.handle_internal_server_error'  # pylint: disable=invalid-name
handler404 = 'analyticsdataserver.views.handle_missing_resource_error'  # pylint: disable=invalid-name
