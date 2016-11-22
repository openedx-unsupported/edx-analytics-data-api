from django.conf.urls import url

from analytics_data_api.v0.views import course_summaries as views

USERNAME_PATTERN = r'(?P<username>[\w.+-]+)'

urlpatterns = [
    url(r'^course_summaries/$', views.CourseSummariesView.as_view(), name='course_summaries'),
]
