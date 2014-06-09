
from django.conf import settings


class DatabaseFromSettingRouter(object):

    def db_for_read(self, model, **hints):
        return self._get_database(model)

    def _get_database(self, model):
        if getattr(model, 'db_from_setting', None):
            return getattr(settings, model.db_from_setting, 'default')
        else:
            return None

    def db_for_write(self, model, **hints):
        return self._get_database(model)

    def allow_relation(self, obj1, obj2, **hints):
        return self._get_database(obj1) == self._get_database(obj2)

    def allow_syncdb(self, db, model):
        dest_db = self._get_database(model)
        if dest_db is not None:
            return db == dest_db
        else:
            return None
