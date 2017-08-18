from django.conf.urls import url

from analytics_data_api.v1.views import programs as views

urlpatterns = [
    url(r'^programs/$', views.ProgramsView.as_view(), name='programs'),
]
