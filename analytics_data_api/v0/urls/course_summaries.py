from django.urls import path

from analytics_data_api.v0.views import course_summaries as views

app_name = 'course_summaries'

urlpatterns = [
    path('course_summaries/', views.CourseSummariesView.as_view(), name='course_summaries'),
]
