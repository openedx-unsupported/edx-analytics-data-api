from django.conf.urls import patterns, url

from analytics_data_api.v0.views import learners as views

USERNAME_PATTERN = r'(?P<username>.+)'
LEARNERS_URLS = [
    ('', views.LearnerView, 'learner')
]

urlpatterns = []

for path, view, name in LEARNERS_URLS:
    regex = r'^{0}/$'.format(USERNAME_PATTERN)
    urlpatterns += patterns('', url(regex, view.as_view(), name=name))
