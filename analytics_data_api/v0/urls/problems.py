import re

from django.conf.urls import patterns, url

from analytics_data_api.v0.views.problems import ProblemResponseAnswerDistributionView
from analytics_data_api.v0.views.problems import GradeDistributionView
from analytics_data_api.v0.views.problems import SequentialOpenDistributionView

PROBLEM_URLS = [
    ('answer_distribution', ProblemResponseAnswerDistributionView, 'answer_distribution'),
    ('grade_distribution', GradeDistributionView, 'grade_distribution'),
]

urlpatterns = patterns(
    '',
    url(r'^(?P<module_id>.+)/sequential_open_distribution$',
        SequentialOpenDistributionView.as_view(), name='sequential_open_distribution'),
)

for path, view, name in PROBLEM_URLS:
    urlpatterns += patterns('', url(r'^(?P<problem_id>.+)/' + re.escape(path) + r'$', view.as_view(), name=name))
