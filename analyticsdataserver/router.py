from django.conf import settings


class AnalyticsApiRouter(object):
    def db_for_read(self, model, **hints):  # pylint: disable=unused-argument
        # pylint: disable=protected-access
        return self._get_database(model._meta.app_label)

    def _get_database(self, app_label):
        if app_label == 'v0':
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
        else:
            return None
