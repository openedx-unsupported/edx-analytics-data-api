from django.conf.urls import url

from analytics_data_api.v1.views import course_summaries as views

urlpatterns = [
    url(r'^course_summaries/$', views.CourseSummariesView.as_view(), name='course_summaries'),
]
