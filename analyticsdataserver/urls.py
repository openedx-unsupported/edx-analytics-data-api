from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic import RedirectView
from analyticsdataserver import views


urlpatterns = patterns(
    '',
    url(r'^$', RedirectView.as_view(url='/docs')),  # pylint: disable=no-value-for-parameter

    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth/', 'rest_framework.authtoken.views.obtain_auth_token'),

    url(r'^api/', include('analytics_data_api.urls', namespace='api')),
    url(r'^docs/', include('rest_framework_swagger.urls')),

    url(r'^status$', views.StatusView.as_view()),
    url(r'^authenticated$', views.AuthenticationTestView.as_view()),
    url(r'^health$', views.HealthView.as_view()),
)

if settings.ENABLE_ADMIN_SITE:  # pragma: no cover
    admin.autodiscover()
    urlpatterns += patterns('', url(r'^site/admin/', include(admin.site.urls)))

handler500 = 'analyticsdataserver.views.handle_internal_server_error'  # pylint: disable=invalid-name
handler404 = 'analyticsdataserver.views.handle_missing_resource_error'  # pylint: disable=invalid-name
