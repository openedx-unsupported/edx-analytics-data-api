from django.conf.urls import patterns, url

from analytics_data_api.v0.views import orgs as views

ORG_ID_PATTERN = r'(?P<org_id>[^/+]+)'

COURSE_URLS = [
    ('problems_and_tags', views.ProblemsAndTagsListView, 'org_problems_and_tags'),
]

urlpatterns = []

for path, view, name in COURSE_URLS:
    regex = r'^{0}/{1}/$'.format(ORG_ID_PATTERN, path)
    urlpatterns += patterns('', url(regex, view.as_view(), name=name))
