from django.conf.urls import patterns, url

from analytics_data_api.v0.views import users as views

USER_URLS = [
    (r'^(?P<username>[^/]+)/$', views.UserProfileView, 'user_profile'),
]

urlpatterns = []

for path, view, name in USER_URLS:
    urlpatterns += patterns('', url(path, view.as_view(), name=name))
