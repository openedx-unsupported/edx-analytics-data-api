from rest_framework import permissions
from rest_framework.response import Response
from django.conf import settings
from django.db import connections
from rest_framework.views import APIView


class StatusView(APIView):
    """
    Simple check to determine if the server is alive

    Return no data, a simple 200 OK status code is sufficient to indicate that the server is alive. This endpoint is
    public and does not require an authentication token to access it.

    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        return Response()


class AuthenticationTestView(APIView):
    """
    Verifies that the client is authenticated

    Returns HTTP 200 if client is authenticated, HTTP 401 if not authenticated

    """

    def get(self, request, *args, **kwargs):
        return Response()


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

    def get(self, request, *args, **kwargs):
        overall_status = 'UNAVAILABLE'
        db_conn_status = 'UNAVAILABLE'

        try:
            connection_name = getattr(settings, 'ANALYTICS_DATABASE', 'default')
            cursor = connections[connection_name].cursor()
            try:
                cursor.execute("SELECT 1")
                cursor.fetchone()
                overall_status = 'OK'
                db_conn_status = 'OK'
            finally:
                cursor.close()
        except Exception:  # pylint: disable=broad-except
            pass

        response = {
            "overall_status": overall_status,
            "detailed_status": {
                'database_connection': db_conn_status
            }
        }

        return Response(response)
