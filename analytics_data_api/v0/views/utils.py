"""Utilities for view-level API logic."""
from django.http import Http404

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

from analytics_data_api.v0.exceptions import CourseKeyMalformedError


def split_query_argument(argument):
    """
    Splits a comma-separated querystring argument into a list.
    Returns None if the argument is empty.
    """
    if argument:
        return argument.split(',')
    else:
        return None


def raise_404_if_none(func):
    """
    Decorator for raising Http404 if function evaluation is falsey (e.g. empty queryset).
    """
    def func_wrapper(self):
        queryset = func(self)
        if queryset:
            return queryset
        else:
            raise Http404
    return func_wrapper


def validate_course_id(course_id):
    """Raises CourseKeyMalformedError if course ID is invalid."""
    try:
        CourseKey.from_string(course_id)
    except InvalidKeyError:
        raise CourseKeyMalformedError(course_id=course_id)
