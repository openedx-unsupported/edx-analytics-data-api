from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic import RedirectView


urlpatterns = patterns(
    '',
    url(r'^$', RedirectView.as_view(url='/docs')),

    # Support logging in to the browseable API
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    # Support generating tokens using a POST request
    url(r'^api-token-auth/', 'rest_framework.authtoken.views.obtain_auth_token'),

    # Route all reports URLs to this endpoint
    url(r'^api/', include('analytics_data_api.urls', namespace='api')),
    url(r'^docs/', include('rest_framework_swagger.urls')),
)

if settings.ENABLE_ADMIN_SITE:
    admin.autodiscover()
    urlpatterns += patterns('', url(r'^site/admin/', include(admin.site.urls)))

handler500 = 'analyticsdataserver.views.handle_internal_server_error'  # pylint: disable=invalid-name
handler404 = 'analyticsdataserver.views.handle_missing_resource_error'  # pylint: disable=invalid-name
