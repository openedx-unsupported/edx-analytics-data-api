from django.conf.urls import include, url
from django.urls import reverse_lazy
from django.views.generic import RedirectView

from analytics_data_api.v0.urls import COURSE_ID_PATTERN
from analytics_data_api.v0.views import courses

app_name = 'v1'

COURSE_URLS = [
    ('activity', courses.CourseActivityWeeklyView, 'activity'),
    ('recent_activity', courses.CourseActivityMostRecentWeekView, 'recent_activity'),
    ('enrollment', courses.CourseEnrollmentView, 'enrollment_latest'),
    ('enrollment/mode', courses.CourseEnrollmentModeView, 'enrollment_by_mode'),
    ('enrollment/education', courses.CourseEnrollmentByEducationView, 'enrollment_by_education'),
    ('enrollment/gender', courses.CourseEnrollmentByGenderView, 'enrollment_by_gender'),
    ('enrollment/location', courses.CourseEnrollmentByLocationView, 'enrollment_by_location'),
    ('problems', courses.ProblemsListView, 'problems'),
    ('problems_and_tags', courses.ProblemsAndTagsListView, 'problems_and_tags'),
    ('videos', courses.VideosListView, 'videos'),
    ('reports/(?P<report_name>[a-zA-Z0-9_]+)', courses.ReportDownloadView, 'reports'),
    ('user_engagement', courses.UserEngagementView, 'user_engagement'),
]

course_urlpatterns = []

for path, view, name in COURSE_URLS:
    regex = fr'^courses/{COURSE_ID_PATTERN}/{path}/$'
    course_urlpatterns.append(url(regex, view.as_view(), name=name))

urlpatterns = course_urlpatterns + [
    url(r'^problems/', include('analytics_data_api.v0.urls.problems')),
    url(r'^videos/', include('analytics_data_api.v0.urls.videos')),
    url('^', include('analytics_data_api.v0.urls.learners')),
    url('^', include('analytics_data_api.v0.urls.course_summaries')),
    url('^', include('analytics_data_api.v0.urls.programs')),

    # pylint: disable=no-value-for-parameter
    url(r'^authenticated/$', RedirectView.as_view(url=reverse_lazy('authenticated')), name='authenticated'),
    url(r'^health/$', RedirectView.as_view(url=reverse_lazy('health')), name='health'),
    url(r'^status/$', RedirectView.as_view(url=reverse_lazy('status')), name='status'),
]
