# This file contains database routers used for routing database operations to the appropriate databases.
# Below is a digest of the routers in this file.
# AnalyticsAPIRouter: This router routes database operations based on the version of the analytics data API being used.
#                     It allows us to route database traffic to the v1 database when using the v1 API, for example.
# AnalyticsModelsRouter: This router routes database operations based on the model that is being requested. Its
#                     primary purpose is to handle database migrations based on the multiple database settings
#                     in the environment.
#
# Note that if a database router returns None for a router method or does not implement the method, the master router
# delegates to the next router in the list until a value is returned. The master router falls back to a default behavior
# if no custom router returns a value.

from django.conf import settings

from analytics_data_api.middleware import thread_data

ANALYTICS_APP_LABELS = ['v0', 'v1']
ENTERPRISE_APP_LABELS = ['enterprise_data']
DJANGO_AUTH_MODELS = ['enterprisedatafeaturerole', 'enterprisedataroleassignment']


class AnalyticsAPIRouter:
    """
    This router's role is to route database operations to the appropriate database when there is an 'analytics_database'
    "hint" in the local thread data. This "hint" is set by the RequestVersionMiddleware and is meant to route
    database operations to particular databases depending on the version of the API requested via the view.
    """
    def _get_database(self, app_label):
        if app_label in ANALYTICS_APP_LABELS and hasattr(thread_data, 'analyticsapi_database'):
            return getattr(thread_data, 'analyticsapi_database')
        # If there is no analyticsapi_database database hint, then fall back to next router.
        return None

    # pylint: disable=unused-argument
    # pylint: disable=protected-access
    def db_for_read(self, model, **hints):
        return self._get_database(model._meta.app_label)

    # pylint: disable=unused-argument
    # pylint: disable=protected-access
    def db_for_write(self, model, **hints):
        return self._get_database(model._meta.app_label)


class AnalyticsModelsRouter:
    """
    This router's role is to route database operations. It is meant, in part, to mirror
    the way databases are structured in the production environment. For example, the ANALYTICS_DATABASE
    and ANALYTICS_DATABASE_V1 databases in production do not contain models from "non-analytics" apps,
    like the auth app. This is because said databases are populated by other means (e.g. EMR jobs, prefect flows).

    This router also ensures that analytics apps are not migrated into the default database unless the default
    database is the only configured database.

    This router also handles an edge case with the enterprise_data app where migrations exist for models that have
    been moved to a different app that is now in the default database.

    Details:
        The enterprise_data application has the migration 0018_enterprisedatafeaturerole_enterprisedataroleassignment,
        which creates a model with a ForeignKey field pointing to the auth_user model. This does not work in a multiple
        DB environment since MySQL does not allow cross-database relations. This model has since been moved to a
        different application that will migrate into the default database where auth_user exists.

    We do not define an allow_relation method. We fall back to Django's default behavior, which is to allow relations
    between model instances that were loaded from the same database.
    """
    def _get_database(self, app_label, model_name):
        # select first available database if there are multiple options
        return self._get_databases(app_label, model_name)[0]

    def _get_databases(self, app_label, model_name):
        databases = []
        if app_label in ANALYTICS_APP_LABELS:
            databases = [
                getattr(settings, 'ANALYTICS_DATABASE', None),
                getattr(settings, 'ANALYTICS_DATABASE_V1', None)
            ]

        # checking against None is an unfortunate bit of code here. There are migrations in
        # the enterprise app that run python against auth related models which will fail on
        # anything other than the default database. There's no way to identify these migrations
        # specifically because there is no value for model.
        # This is brittle, however tables in the analytic databases are created by other means today.
        # (e.g. EMR jobs, prefect flows) We shouldn't expect migrations of this type in the
        # future that do need to run against the analytics database.
        elif (
                app_label in ENTERPRISE_APP_LABELS and
                model_name is not None and
                model_name not in DJANGO_AUTH_MODELS
        ):
            databases = [getattr(settings, 'ANALYTICS_DATABASE', None)]

        databases = list(filter(None, databases))
        if len(databases) > 0:
            return databases

        return ['default']

    # pylint: disable=unused-argument
    # pylint: disable=protected-access
    def db_for_read(self, model, **hints):
        return self._get_database(model._meta.app_label, model._meta.model_name)

    # pylint: disable=unused-argument
    # pylint: disable=protected-access
    def db_for_write(self, model, **hints):
        return self._get_database(model._meta.app_label, model._meta.model_name)

    # pylint: disable=unused-argument
    def allow_migrate(self, database, app_label, model_name=None, **hints):
        databases = self._get_databases(app_label, model_name)
        return database in databases
