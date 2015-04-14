from django.conf.urls import patterns, url, include
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

urlpatterns = patterns(
    '',
    url(r'^courses/', include('analytics_data_api.v0.urls.courses', namespace='courses')),
    url(r'^problems/', include('analytics_data_api.v0.urls.problems', namespace='problems')),
    url(r'^videos/', include('analytics_data_api.v0.urls.videos', namespace='videos')),

    # pylint: disable=no-value-for-parameter
    url(r'^authenticated/$', RedirectView.as_view(url=reverse_lazy('authenticated')), name='authenticated'),
    url(r'^health/$', RedirectView.as_view(url=reverse_lazy('health')), name='health'),
    url(r'^status/$', RedirectView.as_view(url=reverse_lazy('status')), name='status'),
)
