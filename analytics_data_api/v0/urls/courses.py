from django.conf.urls import patterns, url
import re
from analytics_data_api.v0.views.courses import *

course_urls = [
    ('recent_activity', CourseActivityMostRecentWeekView, 'recent_activity'),
    ('enrollment/birth_year', CourseEnrollmentByBirthYearView, 'enrollment_by_birth_year'),
    ('enrollment/education', CourseEnrollmentByEducationView, 'enrollment_by_education'),
]

urlpatterns = patterns(
    '',
    # url(r'^$', CourseDetailView.as_view(), name='detail')
)

for path, view, name in course_urls:
    # TODO Use an integer for the PK
    urlpatterns += patterns('', url(r'^(?P<pk>.+)/' + re.escape(path) + r'$', view.as_view(), name=name))
