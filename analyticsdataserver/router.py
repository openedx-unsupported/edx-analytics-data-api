# This file contains database routers used for routing database operations to the appropriate databases.
# Below is a digest of the routers in this file.
# AnalyticsDevelopmentRouter: This router routes database operations in a development environment. Currently, it only
#                             effects migrations. For example, in development, we want to be able to migrate the
#                             v0 and v1 apps into the v0 and v1 databases, respectively.
# AnalyticsAPIRouter: This router routes database operations based on the version of the analytics data API being used.
#                     It allows us to route database traffic to the v1 database when using the v1 API, for example.
# AnalyticsModelsRouter: This router routes database operations based on the model that is being requested.
#
# The DATABASE_ROUTERS Django setting defines what database routers are used and in what order in a given environment.
#
# Note that if a database router returns None for a router method or does not implement the method, the master router
# delegates to the next router in the list until a value is returned. The master router falls back to a default behavior
# if no custom router returns a value.

from django.conf import settings

from analytics_data_api.middleware import thread_data

ANALYTICS_APP_LABELS = ['v0', 'v1', 'enterprise_data']


class AnalyticsDevelopmentRouter:
    """
    This router's role is to route database operations in the development environment. It is meant, in part, to simulate
    the way databases are structured in the production environment. For example, the ANALYTICS_DATABASE
    and ANALYTICS_DATABASE_V1 databases in production do not contain models from "non-analytics" apps,
    like the auth app. This is because said databases are populated by other means (e.g. EMR jobs, prefect flows).
    Therefore, we attempt to only allow these apps to be migrated where necessary; see inline comment for more details.

    This router also ensures that analytics apps are not migrated into the default database unless the default
    database is the only configured database.

    This router also handles an edge case with the enterprise_data app and the ANALYTICS_DATABASE_V1 database;
    see inline comment for more details.
    """
    # pylint: disable=unused-argument
    def allow_migrate(self, database, app_label, model_name=None, **hints):
        if app_label in ANALYTICS_APP_LABELS:
            databases = getattr(settings, 'DATABASES').keys()
            # We don't want to migrate enterprise_data into the ANALYTICS_DATABASE_V1 database. The reason is two-fold.
            # 1) The ANALYTICS_DATABASE_V1 tables in production do not include enterprise_data tables.
            # 2) The migration 0018_enterprisedatafeaturerole_enterprisedataroleassignment in the enterprise_data app
            #    creates models. When running migrations on the v1 database, this migration successfully creates those
            #    models in the v1 database. The migration 0019_add_enterprise_data_feature_roles creates model instances
            #    for those models created in the previous migration. The write process triggers the db_for_write method
            #    of Django routers. The db_for_write method returns the value of
            #    getattr(settings, 'ANALYTICS_DATABASE', 'default'), which writes the data to the wrong database. There
            #    is no straight forward way to force the db_for_write method to return the value of
            #    getattr(settings, 'ANALYTICS_DATABASE_V1') instead. We forgo migrating that app entirely
            #    in this database.
            if app_label == 'enterprise_data' and database == getattr(settings, 'ANALYTICS_DATABASE_V1'):
                return False

            # If the requested database for migrations is the default database, but other analytics
            # databases are set up, they should be favored over the default database, so prevent these
            # migrations from being run on the default database.
            # We only allow migrations on analytics application models on the default database when analytics
            # is not set up.
            if database == 'default' and 'default' in databases and len(databases) > 1:
                return False

            return True

        # Ideally, we'd only want to migrate other applications into the default database to better
        # mimic production. However, the enterprise_data application has the migration
        # 0018_enterprisedatafeaturerole_enterprisedataroleassignment, which creates a model with a ForeignKey field
        # pointing to the auth_user model. MySQL does not allow cross-database relations, because they violate
        # referential integrity, so we cannot only migrate auth_user into the default database.
        # For that reason, we need to allow the migration of the auth_user table into the ANALYTICS_DATABASE
        # as well.
        # Please see https://docs.djangoproject.com/en/3.2/topics/db/multi-db/#limitations-of-multiple-databases.
        return database in ['default', getattr(settings, 'ANALYTICS_DATABASE')]


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
    This router's role is to route database operations for all other database operations.

    We do not define an allow_relation method. We fall back to Django's default behavior, which is to allow relations
    between model instances that were loaded from the same database.
    """

    def _get_database(self, app_label):
        if app_label in ANALYTICS_APP_LABELS:
            return getattr(settings, 'ANALYTICS_DATABASE', 'default')
        return None

    # pylint: disable=unused-argument
    # pylint: disable=protected-access
    def db_for_read(self, model, **hints):
        return self._get_database(model._meta.app_label)

    # pylint: disable=unused-argument
    # pylint: disable=protected-access
    def db_for_write(self, model, **hints):
        return self._get_database(model._meta.app_label)

    # pylint: disable=unused-argument
    def allow_migrate(self, database, app_label, model_name=None, **hints):
        dest_db = self._get_database(app_label)
        if dest_db is not None:
            return database == dest_db
        return None
