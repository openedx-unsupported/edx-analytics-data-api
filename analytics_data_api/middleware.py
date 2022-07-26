import abc
from threading import local

from django.conf import settings
from django.http.response import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status

from analytics_data_api.v0.exceptions import (
    CannotCreateReportDownloadLinkError,
    CourseKeyMalformedError,
    CourseNotSpecifiedError,
    ReportFileNotFoundError,
)

thread_data = local()


class RequestVersionMiddleware:
    """
    Add a database hint, analyticsapi_database, in the form of an attribute in thread-local storage.
    This is used by the AnalyticsAPIRouter to switch databases between the v0 and v1 views.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if 'api/v1' in request.path:
            thread_data.analyticsapi_database = getattr(settings, 'ANALYTICS_DATABASE_V1')
        else:
            thread_data.analyticsapi_database = getattr(settings, 'ANALYTICS_DATABASE', 'default')
        response = self.get_response(request)
        return response


class BaseProcessErrorMiddleware(MiddlewareMixin, metaclass=abc.ABCMeta):
    """
    Base error.
    """

    @abc.abstractproperty
    def error(self):
        """ Error class to catch. """

    @abc.abstractproperty
    def error_code(self):
        """ Error code to return. """

    @abc.abstractproperty
    def status_code(self):
        """ HTTP status code to return. """

    def process_exception(self, _request, exception):
        if isinstance(exception, self.error):
            return JsonResponse({
                "error_code": self.error_code,
                "developer_message": str(exception)
            }, status=self.status_code)
        return None


class CourseNotSpecifiedErrorMiddleware(BaseProcessErrorMiddleware):
    """
    Raise 400 course not specified.
    """

    @property
    def error(self):
        return CourseNotSpecifiedError

    @property
    def error_code(self):
        return 'course_not_specified'

    @property
    def status_code(self):
        return status.HTTP_400_BAD_REQUEST


class CourseKeyMalformedErrorMiddleware(BaseProcessErrorMiddleware):
    """
    Raise 400 if course key is malformed.
    """

    @property
    def error(self):
        return CourseKeyMalformedError

    @property
    def error_code(self):
        return 'course_key_malformed'

    @property
    def status_code(self):
        return status.HTTP_400_BAD_REQUEST


class ReportFileNotFoundErrorMiddleware(BaseProcessErrorMiddleware):
    """
    Raise 404 if the report file isn't present
    """

    @property
    def error(self):
        return ReportFileNotFoundError

    @property
    def error_code(self):
        return 'report_file_not_found'

    @property
    def status_code(self):
        return status.HTTP_404_NOT_FOUND


class CannotCreateDownloadLinkErrorMiddleware(BaseProcessErrorMiddleware):
    """
    Raise 501 if the filesystem doesn't support creating download links
    """

    @property
    def error(self):
        return CannotCreateReportDownloadLinkError

    @property
    def error_code(self):
        return 'cannot_create_report_download_link'

    @property
    def status_code(self):
        return status.HTTP_501_NOT_IMPLEMENTED
