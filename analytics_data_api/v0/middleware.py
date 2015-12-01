import abc
from django.http.response import JsonResponse
from rest_framework import status

from analytics_data_api.v0.exceptions import (
    CourseKeyMalformedError,
    CourseNotSpecifiedError,
    ParameterValueError,
    LearnerNotFoundError,
)


class BaseProcessErrorMiddleware(object):
    """
    Base error.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def error(self):
        """ Error class to catch. """
        pass

    @abc.abstractproperty
    def error_code(self):
        """ Error code to return. """
        pass

    @abc.abstractproperty
    def status_code(self):
        """ HTTP status code to return. """
        pass

    def process_exception(self, _request, exception):
        if isinstance(exception, self.error):
            return JsonResponse({
                "error_code": self.error_code,
                "developer_message": str(exception)
            }, status=self.status_code)


class LearnerNotFoundErrorMiddleware(BaseProcessErrorMiddleware):
    """
    Raise 404 if learner not found.
    """

    @property
    def error(self):
        return LearnerNotFoundError

    @property
    def error_code(self):
        return 'no_learner_for_course'

    @property
    def status_code(self):
        return status.HTTP_404_NOT_FOUND


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


class ParameterValueErrorMiddleware(BaseProcessErrorMiddleware):
    """
    Raise 400 if illegal parameter values are provided.
    """

    @property
    def error(self):
        return ParameterValueError

    @property
    def error_code(self):
        return 'illegal_parameter_values'

    @property
    def status_code(self):
        return status.HTTP_400_BAD_REQUEST
