
from rest_framework import generics
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import connections
from django.http import HttpResponse, Http404

from analyticsdata.models import CourseActivityByWeek, UsageProblemResponseAnswerDistribution
from analyticsdata.models import CourseActivityByWeekSerializer, UsageProblemResponseAnswerDistributionSerializer


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


class CourseActivityMostRecentWeekView(generics.RetrieveAPIView):

    """
    Counts of users who performed various actions at least once during the most recently computed week.

    The default is all users who performed *any* action in the course.

    The representation has the following fields:

    - course_id: The ID of the course whose activity is described.
    - interval_start: All data from this timestamp up to the `interval_end` was considered when computing this data
      point.
    - interval_end: All data from `interval_start` up to this timestamp was considered when computing this data point.
      Note that data produced at exactly this time is **not** included.
    - label: The type of activity requested. Possible values are:
        - ACTIVE: The number of unique users who performed any action within the course, including actions not
          enumerated below.
        - PLAYED_VIDEO: The number of unique users who started watching any video in the course.
        - ATTEMPTED_PROBLEM: The number of unique users who answered any loncapa based question in the course.
        - POSTED_FORUM: The number of unique users who created a new post, responded to a post, or submitted a comment
          on any forum in the course.
    - count: The number of users who performed the activity indicated by the `label`.

    Parameters:

    - course_id (string): Unique identifier for the course.
    - label (string): The type of activity. Defaults to `ACTIVE`. Possible values:
        - `ACTIVE`
        - `PLAYED_VIDEO`
        - `ATTEMPTED_PROBLEM`
        - `POSTED_FORUM`

    """

    serializer_class = CourseActivityByWeekSerializer

    def get_object(self):  # pylint: disable=arguments-differ
        """Select the activity report for the given course and label."""
        course_id = self.kwargs.get('course_id')
        label = self.request.QUERY_PARAMS.get('label', 'ACTIVE')

        try:
            return CourseActivityByWeek.get_most_recent(course_id, label)
        except ObjectDoesNotExist:
            raise Http404


class UsageProblemResponseAnswerDistributionView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = UsageProblemResponseAnswerDistributionSerializer

    def get_queryset(self):
        usage_id = self.kwargs.get('usage_id')
        return UsageProblemResponseAnswerDistribution.objects.filter(module_id=usage_id)