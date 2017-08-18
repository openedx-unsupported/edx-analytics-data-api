from django.conf.urls import url

from analytics_data_api.v1.views import course_totals as views

urlpatterns = [
    url(r'^course_totals/$', views.CourseTotalsView.as_view(), name='course_totals'),
]
