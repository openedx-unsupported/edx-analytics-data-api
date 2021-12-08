from django.conf import settings

from analytics_data_api.middleware import thread_data


class AnalyticsApiRouter:
    def db_for_read(self, model, **hints):  # pylint: disable=unused-argument
        # pylint: disable=protected-access
        return self._get_database(model._meta.app_label)

    def _get_database(self, app_label):
        if app_label in ('v0', 'v1', 'enterprise_data'):
            if hasattr(thread_data, 'analyticsapi_database'):
                return getattr(thread_data, 'analyticsapi_database')
            return getattr(settings, 'ANALYTICS_DATABASE', 'default')
        return None

    def db_for_write(self, model, **hints):  # pylint: disable=unused-argument
        # pylint: disable=protected-access
        return self._get_database(model._meta.app_label)

    def allow_relation(self, obj1, obj2, **hints):  # pylint: disable=unused-argument
        # pylint: disable=protected-access
        return self._get_database(obj1._meta.app_label) == self._get_database(obj2._meta.app_label)

    def allow_migrate(self, database, app_label, model_name=None, **hints):  # pylint: disable=unused-argument
        dest_db = self._get_database(app_label)
        if dest_db is not None:
            return database == dest_db
        return None
