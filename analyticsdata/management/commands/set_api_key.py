"""
A command to set the API key for a user using when using TokenAuthentication.

"""

from optparse import make_option

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = 'Set the API key for the specified user.'
    args = '<username> <api_key>'
    option_list = BaseCommand.option_list + (
        make_option('--create-user', action='store_true', default=False,
                    help="Create a user if it doesn't exists"),
        make_option('--delete-key', action='store_true', default=False,
                    help="Delete API key for user"
        )
    )

    def handle(self, *args, **options):
        if options['delete_key']:
            self.delete_user(*args)
        else:
            self.set_api_key(*args, **options)

    def delete_user(self, *args):
        if len(args) != 1:
            raise CommandError('Invalid or misssing arguments')

        username = args[0]

        qs = Token.objects.filter(user__username=username)

        if qs.exists():
            qs.delete()
            self.stdout.write('Removed API key for user: <{0}>\n'.format(username))
        else:
            self.stdout.write('Unknown user or user without an API key: <{0}>\n'.format(username))

    def set_api_key(self, *args, **options):
        if len(args) != 2:
            raise CommandError('Invalid or missing arguments')

        username, key = args

        user = self.get_user(username, options['create_user'])

        self.set_token(user, key)

    def get_user(self, username, create_user=False):
        if create_user:
            user, created = User.objects.get_or_create(username=username)
            if created:
                self.stdout.write('Created user: <{0}>\n'.format(user))
        else:
            try:
                user = User.objects.get(username=username)
            except ObjectDoesNotExist:
                raise CommandError('Unknown user: <{0}>'.format(username))

        return user

    def set_token(self, user, key):
        # Check that no other user has the same key
        qs = Token.objects.filter(key=key)
        if qs.exists() and qs[0].user != user:
            raise CommandError('Key already in use.')

        # Get and update the user key
        _, created = Token.objects.get_or_create(user=user)
        count = Token.objects.filter(user=user).update(key=key)

        if count:
            action = 'Created' if created else 'Updated'
            self.stdout.write('{0} API key for user: <{1}>\n'.format(action, user))
        else:
            raise CommandError('Something went wrong.')