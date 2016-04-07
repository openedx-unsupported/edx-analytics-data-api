import datetime
from importlib import import_module

from django.db.models import Q
from rest_framework.authtoken.models import Token


def delete_user_auth_token(username):
    """
    Deletes the authentication tokens for the user with the given username

    If no user exists, NO error is returned.
    :param username: Username of the user whose authentication tokens should be deleted
    :return: None
    """
    Token.objects.filter(user__username=username).delete()


def set_user_auth_token(user, key):
    """
    Sets the authentication for the given User.

    Raises an AttributeError if *different* User with the specified key already exists.

    :param user: User whose authentication is being set
    :param key: New authentication key
    :return: None
    """
    # Check that no other user has the same key
    if Token.objects.filter(~Q(user=user), key=key).exists():
        raise AttributeError("The key %s is already in use by another user.", key)

    Token.objects.filter(user=user).delete()
    Token.objects.create(user=user, key=key)

    print "Set API key for user %s to %s" % (user, key)


def matching_tuple(answer):
    """ Return tuple containing values which must match for consolidation. """
    return (
        answer.question_text,
        answer.answer_value,
        answer.problem_display_name,
        answer.correct,
    )


def dictfetchall(cursor):
    """Returns all rows from a cursor as a dict"""

    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]


def load_fully_qualified_definition(definition):
    """ Returns the class given the full definition. """
    module_name, class_name = definition.rsplit('.', 1)
    module = import_module(module_name)
    return getattr(module, class_name)


def date_range(start_date, end_date, delta=datetime.timedelta(days=1)):
    """
    Returns a generator that iterates over the date range [start_date, end_date)
    (start_date inclusive, end_date exclusive).  Each date in the range is
    offset from the previous date by a change of `delta`, which defaults
    to one day.

    Arguments:
        start_date (datetime.datetime): The start date of the range, inclusive
        end_date (datetime.datetime): The end date of the range, exclusive
        delta (datetime.timedelta): The change in time between dates in the
            range.

    Returns:
        Generator: A generator which iterates over all dates in the specified
        range.
    """
    cur_date = start_date
    while cur_date < end_date:
        yield cur_date
        cur_date += delta
