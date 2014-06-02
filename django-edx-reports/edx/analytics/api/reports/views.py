from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connections


@api_view(['GET'])
@permission_classes((AllowAny, ))
def status(_request):
    return Response()


@api_view(['GET'])
def authenticated(_request):
    return Response()


@api_view(['GET'])
@permission_classes((AllowAny, ))
def health(_request):
    overall_status = 'OK'
    db_conn_statuses = {}

    for connection_name in connections:
        try:
            cursor = connections[connection_name].cursor()
            try:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            finally:
                cursor.close()
        except Exception:  # pylint: disable=broad-except
            overall_status = 'UNAVAILABLE'
            db_conn_statuses[connection_name] = 'UNAVAILABLE'
        else:
            db_conn_statuses[connection_name] = 'OK'

    response = {
        "overall_status": overall_status,
        "detailed_status": {
            'database_connections': db_conn_statuses
        }
    }

    return Response(response)
