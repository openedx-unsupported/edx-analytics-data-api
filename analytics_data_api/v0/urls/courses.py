import re

from django.conf.urls import patterns, url

from analytics_data_api.v0.views import courses as views


COURSE_URLS = [
    ('recent_activity', views.CourseActivityMostRecentWeekView, 'recent_activity'),
    ('enrollment', views.CourseEnrollmentView, 'enrollment_latest'),
    ('enrollment/birth_year', views.CourseEnrollmentByBirthYearView, 'enrollment_by_birth_year'),
    ('enrollment/education', views.CourseEnrollmentByEducationView, 'enrollment_by_education'),
    ('enrollment/gender', views.CourseEnrollmentByGenderView, 'enrollment_by_gender'),
    ('enrollment/location', views.CourseEnrollmentByLocationView, 'enrollment_by_location'),
]

urlpatterns = []

for path, view, name in COURSE_URLS:
    urlpatterns += patterns('', url(r'^(?P<course_id>.+)/' + re.escape(path) + r'/$', view.as_view(), name=name))
