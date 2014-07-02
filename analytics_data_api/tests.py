from django.contrib.auth.models import User
from django.core.management import call_command, CommandError
from django.test import TestCase

from django_dynamic_fixture import G
from rest_framework.authtoken.models import Token
from analytics_data_api.utils import delete_user_auth_token, set_user_auth_token


class UtilsTests(TestCase):
    def test_delete_user_auth_token(self):
        # Create user and token
        user = G(User)
        G(Token, user=user)

        # Verify token exists
        self.assertTrue(Token.objects.filter(user=user).exists())

        # Call delete method
        delete_user_auth_token(user.username)

        # Verify token no longer exists
        self.assertFalse(Token.objects.filter(user=user).exists())

    def test_delete_user_auth_token_non_existing(self):
        user = G(User)
        self.assertFalse(Token.objects.filter(user=user).exists())
        delete_user_auth_token(user.username)
        self.assertFalse(Token.objects.filter(user=user).exists())

    def test_set_user_auth_token(self):
        user = G(User)
        key = "Avengers Assemble!"
        self.assertFalse(Token.objects.filter(user=user).exists())
        set_user_auth_token(user, key)
        self.assertEqual(Token.objects.get(user=user).key, key)

        key = "Hulk Smash!"
        set_user_auth_token(user, key)
        self.assertEqual(Token.objects.get(user=user).key, key)

        # Verify we don't create token conflicts
        user2 = G(User)
        self.assertRaises(AttributeError, set_user_auth_token, user2, key)


class SetApiKeyTests(TestCase):
    def test_delete_key(self):
        user = G(User)
        G(Token, user=user)
        self.assertTrue(Token.objects.filter(user=user).exists())
        call_command('set_api_key', user.username, delete_key=True)
        self.assertFalse(Token.objects.filter(user=user).exists())

    def test_invalid_arguments(self):
        self.assertRaises(CommandError, call_command, 'set_api_key')
        self.assertRaises(CommandError, call_command, 'set_api_key', 'username')

    def test_set_key(self):
        user = G(User)
        key = "Super Secret!"
        self.assertFalse(Token.objects.filter(user=user).exists())
        call_command('set_api_key', user.username, key)
        self.assertEqual(Token.objects.get(user=user).key, key)

        key = "No one will guess this!"
        call_command('set_api_key', user.username, key)
        self.assertEqual(Token.objects.get(user=user).key, key)

    def test_set_key_conflict(self):
        key = "Super Secret!"
        user = G(User)
        user2 = G(User)
        G(Token, user=user, key=key)

        self.assertFalse(Token.objects.filter(user=user2).exists())
        call_command('set_api_key', user2.username, key)
        self.assertFalse(Token.objects.filter(user=user2).exists())
