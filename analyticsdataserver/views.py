import logging

from django.conf import settings
from django.db import connections
from django.http import HttpResponse
from rest_framework import permissions
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def handle_internal_server_error(_request):
    """Notify the client that an error occurred processing the request without providing any detail."""
    return _handle_error(500)


def handle_missing_resource_error(_request, exception=None):  # pylint: disable=unused-argument
    """Notify the client that the requested resource could not be found."""
    return _handle_error(404)


def _handle_error(status_code):
    info = {
        'status': status_code
    }

    renderer = JSONRenderer()
    content_type = f'{renderer.media_type}; charset={renderer.charset}'
    return HttpResponse(renderer.render(info), content_type=content_type, status=status_code)


class StatusView(APIView):
    """
    Simple check to determine if the server is alive

    Return no data, a simple 200 OK status code is sufficient to indicate that the server is alive. This endpoint is
    public and does not require an authentication token to access it.

    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return Response({})


class AuthenticationTestView(APIView):
    """
    Verifies that the client is authenticated

    Returns HTTP 200 if client is authenticated, HTTP 401 if not authenticated

    """

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return Response({})


class HealthView(APIView):
    """
   A more comprehensive check to see if the system is fully operational.

   This endpoint is public and does not require an authentication token to access it.

   The returned structure contains the following fields:

   - overall_status: Can be either "OK" or "UNAVAILABLE".
   - detailed_status: More detailed information about the status of the system.
       - database_connection: Status of the database connection. Can be either "OK" or "UNAVAILABLE".

   """
    permission_classes = (permissions.AllowAny,)
    STATUS_OK = 'OK'
    STATUS_UNAVAILABLE = 'UNAVAILABLE'

    def _get_connection_status(self, connection_name):
        """
        With the passed in database name, try to make connection to the database.
        If database is able to connect successfully, return 'OK' status.
        Otherwise, return 'UNAVAILABLE' status
        """
        db_status = self.STATUS_UNAVAILABLE
        try:
            cursor = connections[connection_name].cursor()
            try:
                cursor.execute("SELECT 1")
                cursor.fetchone()
                db_status = self.STATUS_OK
            finally:
                cursor.close()
        except Exception:  # pylint: disable=broad-except
            pass
        return db_status

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        overall_status = self.STATUS_UNAVAILABLE
        analytics_db_status = self.STATUS_UNAVAILABLE

        # First try the default database.
        # The default database hosts user and auth info. Without it, no API would function
        default_db_status = self._get_connection_status('default')

        analytics_db_v1_name = getattr(settings, 'ANALYTICS_DATABASE_V1')
        analytics_db_name = getattr(settings, 'ANALYTICS_DATABASE')
        if analytics_db_v1_name:
            # If the v1 db is defined, we check the status of both v0 and v1 analytics db status
            analytics_v0_db_status = self._get_connection_status(analytics_db_name)
            analyitcs_v1_db_status = self._get_connection_status(analytics_db_v1_name)
            if analytics_v0_db_status == analyitcs_v1_db_status == self.STATUS_OK:
                analytics_db_status = self.STATUS_OK
        else:
            # Otherwise, only check the defined 'ANALYTICS_DATABASE' status
            analytics_db_status = self._get_connection_status(analytics_db_name)

        if default_db_status == analytics_db_status == self.STATUS_OK:
            overall_status = self.STATUS_OK

        response = {
            "overall_status": overall_status,
            "detailed_status": {
                'default_db_status': default_db_status,
                'analytics_db_status': analytics_db_status,
            }
        }

        if overall_status == self.STATUS_UNAVAILABLE:
            logger.error("Health check failed: %s", response)

        return Response(response, status=200 if overall_status == self.STATUS_OK else 503)
