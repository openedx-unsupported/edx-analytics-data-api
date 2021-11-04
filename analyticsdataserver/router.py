from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

import threading

request_cfg = threading.local()

class RouterMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, args, kwargs):
        if 'api/v1' in request.path:
            request_cfg.database = getattr(settings, 'ANALYTICS_DATABASE_V1', 'default_v1')
    def process_response(self, request, response):
        if hasattr(request_cfg, 'database'):
            del request_cfg.database
        return response


class AnalyticsApiRouter:
    def db_for_read(self, model, **hints):  # pylint: disable=unused-argument
        # pylint: disable=protected-access
        return self._get_database(model._meta.app_label)

    def _get_database(self, app_label):
        if app_label in ('v1', 'v0', 'enterprise_data'):
            if hasattr(request_cfg, 'database'):
                return request_cfg.database
            else:
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
