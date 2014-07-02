from django.db.models import Q
from rest_framework.authtoken.models import Token


def delete_user_auth_token(username):
    Token.objects.filter(user__username=username).delete()


def set_user_auth_token(user, key):
    # Check that no other user has the same key
    if Token.objects.filter(~Q(user=user), key=key).exists():
        raise AttributeError("The key %s is already in use by another user.", key)

    Token.objects.filter(user=user).delete()
    Token.objects.create(user=user, key=key)

    print "Set API key for user %s to %s" % (user, key)
