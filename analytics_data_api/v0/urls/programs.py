from django.urls import path

from analytics_data_api.v0.views import programs as views

app_name = 'programs'

urlpatterns = [
    path('programs/', views.ProgramsView.as_view(), name='programs'),
]
