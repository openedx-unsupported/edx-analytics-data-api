from django.conf import settings


def elasticsearch_settings_defined():
    return all(
        setting is not None for setting in (
            settings.ELASTICSEARCH_LEARNERS_HOST,
            settings.ELASTICSEARCH_LEARNERS_INDEX,
            settings.ELASTICSEARCH_LEARNERS_UPDATE_INDEX
        )
    )
