
from rest_framework import generics, mixins
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from django.conf import settings
from django.db import connections
from django.http import HttpResponse

from analyticsdata.models import CourseUserActivityByWeek


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


def handle_internal_server_error(_request):
    """Notify the client that an error occurred processing the request without providing any detail."""
    return _handle_error(500)


def handle_missing_resource_error(_request):
    """Notify the client that the requested resource could not be found."""
    return _handle_error(404)


def _handle_error(status_code):
    info = {
        'status': status_code
    }

    renderer = JSONRenderer()
    content_type = '{media}; charset={charset}'.format(media=renderer.media_type, charset=renderer.charset)
    return HttpResponse(renderer.render(info), content_type=content_type, status=status_code)


class CourseUserActivityListView(generics.ListAPIView):
    model = CourseUserActivityByWeek
    paginate_by = 100
    max_paginate_by = 500

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        if course_id is None:
            course_id = self.request.QUERY_PARAMS.get('course_id')

        queryset = self.model.objects.all()
        if course_id is not None:
            return queryset.filter(course_id=course_id)
        else:
            return queryset


class CourseUserActivityView(generics.RetrieveAPIView):
    model = CourseUserActivityByWeek
