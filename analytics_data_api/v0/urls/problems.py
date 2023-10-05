import re

from django.urls import re_path

from analytics_data_api.v0.views import problems as views

app_name = 'problems'

PROBLEM_URLS = [
    ('answer_distribution', views.ProblemResponseAnswerDistributionView, 'answer_distribution'),
    ('grade_distribution', views.GradeDistributionView, 'grade_distribution'),
]

urlpatterns = [
    re_path(r'^(?P<module_id>.+)/sequential_open_distribution/$',
            views.SequentialOpenDistributionView.as_view(),
            name='sequential_open_distribution'),
]

for path, view, name in PROBLEM_URLS:
    urlpatterns.append(re_path(r'^(?P<problem_id>.+)/' + re.escape(path) + r'/$', view.as_view(), name=name))
