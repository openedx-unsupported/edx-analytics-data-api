
from rest_framework import generics, mixins
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from django.conf import settings
from django.db import connections
from django.http import HttpResponse

from analyticsdata.models import CourseActivityLastWeek


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


class CourseActivityLastWeekView(generics.RetrieveAPIView):
    """
    Counts of users who performed various actions at least once in the past week. The default is all users who performed *any* action in the course.

    The representation has the following fields:

    - course_id: The ID of the course whose activity is described.
    - interval_start: All data from this timestamp up to the `interval_end` was considered when computing this data point.
    - interval_end: All data from `interval_start` up to this timestamp was considered when computing this data point. Note that data produced at exactly this time is **not** included.
    - label: The type of activity requested. Possible values are:
        - active: The number of unique users who visited the course.
        - started_video: The number of unique users who started watching any video in the course.
        - answered_question: The number of unique users who answered any loncapa based question in the course.
        - posted_forum: The number of unique users who created a new post, responded to a post, or submitted a comment on any forum in the course.
    - count: The number of users who performed the activity indicated by the `label`.

    + Parameters
        + course_id (string) ... ID of the course.

            This string should uniquely identify the course.

        + label = `Active` (optional, string) ... The type of activity.

            + Values
                + `Active`
                + `Started_Video`
                + `Answered_Question`
                + `Posted_Forum`

    """
    model = CourseActivityLastWeek

    # TODO: restrict fields, exclude the id

    def get_object(self):
        # TODO: will this return a 404 if this course doesn't exist?
        course_id = self.kwargs.get('course_id')
        # TODO: will this return a 404 if this label isn't found?
        # TODO: casing is odd for these values. Maybe change this in the pipeline?
        label = self.request.QUERY_PARAMS.get('label', 'Active')

        # TODO: what happens if data isn't generated for > 1 week?
        return self.model.objects.all().filter(course_id=course_id, label=label).latest('interval_end')
