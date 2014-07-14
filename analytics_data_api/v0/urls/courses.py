import re

from django.conf.urls import patterns, url

from analytics_data_api.v0.views.courses import CourseActivityMostRecentWeekView, CourseEnrollmentByEducationView, \
    CourseEnrollmentByBirthYearView, CourseEnrollmentByGenderView, CourseEnrollmentLatestView


COURSE_URLS = [
    ('recent_activity', CourseActivityMostRecentWeekView, 'recent_activity'),
    ('enrollment', CourseEnrollmentLatestView, 'enrollment_latest'),
    ('enrollment/birth_year', CourseEnrollmentByBirthYearView, 'enrollment_by_birth_year'),
    ('enrollment/education', CourseEnrollmentByEducationView, 'enrollment_by_education'),
    ('enrollment/gender', CourseEnrollmentByGenderView, 'enrollment_by_gender'),
]

urlpatterns = []

for path, view, name in COURSE_URLS:
    urlpatterns += patterns('', url(r'^(?P<course_id>.+)/' + re.escape(path) + r'/$', view.as_view(), name=name))
