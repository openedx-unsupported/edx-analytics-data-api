from django.conf.urls import patterns, url

from analytics_data_api.v0.views import courses as views

COURSE_ID_PATTERN = r'(?P<course_id>[^/+]+[/+][^/+]+[/+][^/]+)'
COURSE_URLS = [
    ('activity', views.CourseActivityWeeklyView, 'activity'),
    ('recent_activity', views.CourseActivityMostRecentWeekView, 'recent_activity'),
    ('enrollment', views.CourseEnrollmentView, 'enrollment_latest'),
    ('enrollment/mode', views.CourseEnrollmentModeView, 'enrollment_by_mode'),
    ('enrollment/birth_year', views.CourseEnrollmentByBirthYearView, 'enrollment_by_birth_year'),
    ('enrollment/education', views.CourseEnrollmentByEducationView, 'enrollment_by_education'),
    ('enrollment/gender', views.CourseEnrollmentByGenderView, 'enrollment_by_gender'),
    ('enrollment/location', views.CourseEnrollmentByLocationView, 'enrollment_by_location'),
    ('problems', views.ProblemsListView, 'problems'),
    ('videos', views.VideosListView, 'videos')
]

urlpatterns = []

for path, view, name in COURSE_URLS:
    regex = r'^{0}/{1}/$'.format(COURSE_ID_PATTERN, path)
    urlpatterns += patterns('', url(regex, view.as_view(), name=name))
