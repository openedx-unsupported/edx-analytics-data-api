from django.apps import AppConfig
from django.conf import settings
from elasticsearch_dsl import connections


class ApiAppConfig(AppConfig):

    name = 'analytics_data_api.v0'

    def ready(self):
        super(ApiAppConfig, self).ready()
        if settings.ELASTICSEARCH_LEARNERS_HOST:
            connections.connections.create_connection(hosts=[settings.ELASTICSEARCH_LEARNERS_HOST])
