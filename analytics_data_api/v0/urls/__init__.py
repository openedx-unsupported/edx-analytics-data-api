from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView

app_name = 'analytics_data_api.v0'

COURSE_ID_PATTERN = r'(?P<course_id>[^/+]+[/+][^/+]+[/+][^/]+)'

urlpatterns = [
    path('courses/', include('analytics_data_api.v0.urls.courses')),
    path('problems/', include('analytics_data_api.v0.urls.problems')),
    path('videos/', include('analytics_data_api.v0.urls.videos')),
    path('', include('analytics_data_api.v0.urls.learners')),
    path('', include('analytics_data_api.v0.urls.course_summaries')),
    path('', include('analytics_data_api.v0.urls.programs')),

    # pylint: disable=no-value-for-parameter
    path('authenticated/', RedirectView.as_view(url=reverse_lazy('authenticated')), name='authenticated'),
    path('health/', RedirectView.as_view(url=reverse_lazy('health')), name='health'),
    path('status/', RedirectView.as_view(url=reverse_lazy('status')), name='status'),
]
