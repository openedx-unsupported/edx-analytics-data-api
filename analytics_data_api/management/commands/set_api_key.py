"""A command to set the API key for a user using when using TokenAuthentication."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from analytics_data_api.utils import delete_user_auth_token, set_user_auth_token


User = get_user_model()


class Command(BaseCommand):
    """A command to set the API key for a user using when using TokenAuthentication."""

    help = 'Set the API key for the specified user.'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='?')
        parser.add_argument('api_key', nargs='?')
        parser.add_argument(
            '--delete-key',
            action='store_true',
            default=False,
            help="Delete API key for user",
        )

    def handle(self, *args, **options):
        if options['username'] is None:
            raise CommandError("You must supply a username.")

        username = options['username']

        if options['delete_key']:
            delete_user_auth_token(username)
            print 'Removed API key for user: <{0}>'.format(username)
        else:
            if options['api_key'] is None:
                raise CommandError("You must supply both a username and key.")

            # pylint: disable=no-member
            user, _ = User.objects.get_or_create(username=username)

            try:
                key = options['api_key']
                set_user_auth_token(user, key)
            except AttributeError:
                print "The key %s is in use by another user. Please select another key." % key
