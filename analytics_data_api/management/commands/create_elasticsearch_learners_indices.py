from elasticsearch import Elasticsearch

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from analytics_data_api.management.utils import elasticsearch_settings_defined


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
            self.stderr.write('"{}" index already exists.'.format(settings.ELASTICSEARCH_LEARNERS_INDEX))
        else:
            es.indices.create(
                index=settings.ELASTICSEARCH_LEARNERS_INDEX,
                body={
                    'mappings': {
                        'roster_entry': {
                            'properties': {
                                'name': {
                                    'type': 'string'
                                },
                                'user_id': {
                                    'type': 'integer', 'index': 'not_analyzed'
                                },
                                'username': {
                                    'type': 'string', 'index': 'not_analyzed'
                                },
                                'email': {
                                    'type': 'string', 'index': 'not_analyzed', 'doc_values': True
                                },
                                'course_id': {
                                    'type': 'string', 'index': 'not_analyzed'
                                },
                                'enrollment_mode': {
                                    'type': 'string', 'index': 'not_analyzed', 'doc_values': True
                                },
                                'language': {
                                    'type': 'string', 'index': 'not_analyzed'
                                },
                                'location': {
                                    'type': 'string', 'index': 'not_analyzed'
                                },
                                'year_of_birth': {
                                    'type': 'integer', 'index': 'not_analyzed'
                                },
                                'level_of_education': {
                                    'type': 'string', 'index': 'not_analyzed'
                                },
                                'gender': {
                                    'type': 'string', 'index': 'not_analyzed'
                                },
                                'mailing_address': {
                                    'type': 'string', 'index': 'not_analyzed'
                                },
                                'city': {
                                    'type': 'string', 'index': 'not_analyzed'
                                },
                                'country': {
                                    'type': 'string', 'index': 'not_analyzed'
                                },
                                'goals': {
                                    'type': 'string', 'index': 'not_analyzed'
                                },
                                'segments': {
                                    'type': 'string'
                                },
                                'cohort': {
                                    'type': 'string', 'index': 'not_analyzed', 'doc_values': True
                                },
                                'discussion_contributions': {
                                    'type': 'integer', 'doc_values': True
                                },
                                'problems_attempted': {
                                    'type': 'integer', 'doc_values': True
                                },
                                'problems_completed': {
                                    'type': 'integer', 'doc_values': True
                                },
                                'problem_attempts_per_completed': {
                                    'type': 'float', 'doc_values': True
                                },
                                'attempt_ratio_order': {
                                    'type': 'integer', 'doc_values': True
                                },
                                'videos_viewed': {
                                    'type': 'integer', 'doc_values': True
                                },
                                'enrollment_date': {
                                    'type': 'date', 'doc_values': True
                                },
                            }
                        }
                    }
                }
            )

        if es.indices.exists(settings.ELASTICSEARCH_LEARNERS_UPDATE_INDEX):
            self.stderr.write('"{}" index already exists.'.format(settings.ELASTICSEARCH_LEARNERS_UPDATE_INDEX))
        else:
            es.indices.create(
                index=settings.ELASTICSEARCH_LEARNERS_UPDATE_INDEX,
                body={
                    'mappings': {
                        'marker': {
                            'properties': {
                                'date': {
                                    'type': 'date', 'doc_values': True
                                },
                                'target_index': {
                                    'type': 'string'
                                },
                            }
                        }
                    }
                }
            )
