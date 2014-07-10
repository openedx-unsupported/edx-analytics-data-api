import re

from django.conf.urls import patterns, url

from analytics_data_api.v0.views.problems import ProblemResponseAnswerDistributionView

PROBLEM_URLS = [
    ('answer_distribution', ProblemResponseAnswerDistributionView, 'answer_distribution'),
]

urlpatterns = patterns(
    '',
)

for path, view, name in PROBLEM_URLS:
    # TODO Use an integer for the PK
    urlpatterns += patterns('', url(r'^(?P<problem_id>.+)/' + re.escape(path) + r'$', view.as_view(), name=name))
