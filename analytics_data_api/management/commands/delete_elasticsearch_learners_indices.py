from elasticsearch import Elasticsearch

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Removes Elasticsearch indices used by the Analytics Data API'

    def handle(self, *args, **options):
        es = Elasticsearch([settings.ELASTICSEARCH_LEARNERS_HOST])
        for index in [settings.ELASTICSEARCH_LEARNERS_INDEX, settings.ELASTICSEARCH_LEARNERS_UPDATE_INDEX]:
            if es.indices.exists(settings.ELASTICSEARCH_LEARNERS_UPDATE_INDEX):
                es.indices.delete(index=index)
