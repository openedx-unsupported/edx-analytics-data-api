from collections import defaultdict

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


def consolidate_answers(problem):
    """ Attempt to consolidate erroneously randomized answers. """
    answer_sets = defaultdict(list)
    match_tuple_sets = defaultdict(set)

    for answer in problem:
        answer.consolidated_variant = False

        answer_sets[answer.value_id].append(answer)
        match_tuple_sets[answer.value_id].add(matching_tuple(answer))

    # If a part has more than one unique tuple of matching fields, do not consolidate.
    for _, match_tuple_set in match_tuple_sets.iteritems():
        if len(match_tuple_set) > 1:
            return problem

    consolidated_answers = []

    for _, answers in answer_sets.iteritems():
        consolidated_answer = None

        if len(answers) == 1:
            consolidated_answers.append(answers[0])
            continue

        for answer in answers:
            if not consolidated_answer:
                consolidated_answer = answer

                consolidated_answer.variant = None
                consolidated_answer.consolidated_variant = True
            else:
                consolidated_answer.count += answer.count

        consolidated_answers.append(consolidated_answer)

    return consolidated_answers


def dictfetchall(cursor):
    """Returns all rows from a cursor as a dict"""

    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]
