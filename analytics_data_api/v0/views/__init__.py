from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings
from django.db import connections


@api_view(['GET'])
@permission_classes((AllowAny, ))
def status(_request):
    """
    A very quick check to see if the application server is alive and processing requests.

    Return no data, a simple 200 OK status code is sufficient to indicate that the server is alive. This endpoint is
    public and does not require an authentication token to access it.

    """
    return Response()


@api_view(['GET'])
def authenticated(_request):
    """
    Validate provided credentials.

    Return no data, a simple 200 OK status code is sufficient to indicate that the credentials are valid.

    """
    return Response()


@api_view(['GET'])
@permission_classes((AllowAny, ))
def health(_request):
    """
    A more comprehensive check to see if the system is fully operational.

    This endpoint is public and does not require an authentication token to access it.

    The returned structure contains the following fields:

    - overall_status: Can be either "OK" or "UNAVAILABLE".
    - detailed_status: More detailed information about the status of the system.
        - database_connection: Status of the database connection. Can be either "OK" or "UNAVAILABLE".

    """
    overall_status = 'OK'
    db_conn_status = 'OK'

    connection_name = getattr(settings, 'ANALYTICS_DATABASE', 'default')
    try:
        cursor = connections[connection_name].cursor()
        try:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        finally:
            cursor.close()
    except Exception:  # pylint: disable=broad-except
        overall_status = 'UNAVAILABLE'
        db_conn_status = 'UNAVAILABLE'

    response = {
        "overall_status": overall_status,
        "detailed_status": {
            'database_connection': db_conn_status
        }
    }

    return Response(response)
