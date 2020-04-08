

from django.conf.urls import include, url
from django.urls import reverse_lazy
from django.views.generic import RedirectView

app_name = 'analytics_data_api.v0'

COURSE_ID_PATTERN = r'(?P<course_id>[^/+]+[/+][^/+]+[/+][^/]+)'

urlpatterns = [
    url(r'^courses/', include('analytics_data_api.v0.urls.courses')),
    url(r'^problems/', include('analytics_data_api.v0.urls.problems')),
    url(r'^videos/', include('analytics_data_api.v0.urls.videos')),
    url('^', include('analytics_data_api.v0.urls.learners')),
    url('^', include('analytics_data_api.v0.urls.course_summaries')),
    url('^', include('analytics_data_api.v0.urls.programs')),

    # pylint: disable=no-value-for-parameter
    url(r'^authenticated/$', RedirectView.as_view(url=reverse_lazy('authenticated')), name='authenticated'),
    url(r'^health/$', RedirectView.as_view(url=reverse_lazy('health')), name='health'),
    url(r'^status/$', RedirectView.as_view(url=reverse_lazy('status')), name='status'),
]
