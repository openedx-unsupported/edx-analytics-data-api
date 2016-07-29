"""Utilities for view-level API logic."""
from django.http import Http404


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
    Decorator for raiseing Http404 if function evaulation is falsey (e.g. empty queryset).
    """
    def func_wrapper(self):
        queryset = func(self)
        if queryset:
            return queryset
        else:
            raise Http404
    return func_wrapper