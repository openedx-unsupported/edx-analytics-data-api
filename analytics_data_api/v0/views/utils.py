"""Utilities for view-level API logic."""


def split_query_argument(argument):
    """
    Splits a comma-separated querystring argument into a list.
    Returns None if the argument is empty.
    """
    if argument:
        return argument.split(',')
    else:
        return None
