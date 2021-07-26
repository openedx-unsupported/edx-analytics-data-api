from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from elasticsearch import Elasticsearch

from analytics_data_api.management.utils import elasticsearch_settings_defined
from analytics_data_api.v0.documents import RosterEntry, RosterUpdate


class TestRosterEntry(RosterEntry):
    class Index:
        name = settings.ELASTICSEARCH_LEARNERS_INDEX
        aliases = {settings.ELASTICSEARCH_LEARNERS_INDEX_ALIAS: {}}


class Command(BaseCommand):
    help = 'Creates Elasticsearch indices used by the Analytics Data API.'

    def handle(self, *args, **options):
        if not elasticsearch_settings_defined():
            raise CommandError(
                'You must define settings.ELASTICSEARCH_LEARNERS_HOST, '
                'settings.ELASTICSEARCH_LEARNERS_INDEX, and settings.ELASTICSEARCH_LEARNERS_UPDATE_INDEX'
            )

        es = Elasticsearch([settings.ELASTICSEARCH_LEARNERS_HOST])
        if es.indices.exists(settings.ELASTICSEARCH_LEARNERS_INDEX):
            self.stderr.write(f'"{settings.ELASTICSEARCH_LEARNERS_INDEX}" index already exists.')
        else:
            TestRosterEntry.init(using=es)

        if es.indices.exists(settings.ELASTICSEARCH_LEARNERS_UPDATE_INDEX):
            self.stderr.write(f'"{settings.ELASTICSEARCH_LEARNERS_UPDATE_INDEX}" index already exists.')
        else:
            RosterUpdate.init(using=es)
