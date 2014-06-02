from django.conf.urls import patterns, include, url
from django.contrib import admin


admin.autodiscover()


urlpatterns = patterns(
    '',
    # Change the default URL of the admin site for security reasons
    url(r'^site/admin/', include(admin.site.urls)),

    # Support logging in to the browseable API
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    # Support generating tokens using a POST request
    url(r'^api-token-auth/', 'rest_framework.authtoken.views.obtain_auth_token'),

    # Route all reports URLs to this endpoint
    # TODO: come up with a better way to handle versioning, maybe a decorator?
    url(r'^api/v0/', include('analyticsdata.urls')),
)

handler500 = 'analyticsdata.views.handle_internal_server_error'  # pylint: disable=invalid-name
handler404 = 'analyticsdata.views.handle_missing_resource_error'  # pylint: disable=invalid-name
