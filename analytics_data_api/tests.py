import datetime

from django.contrib.auth.models import User
from django.core.management import call_command, CommandError
from django.test import TestCase
from django_dynamic_fixture import G
from rest_framework.authtoken.models import Token

from analytics_data_api.constants.country import get_country, UNKNOWN_COUNTRY

from analytics_data_api.utils import date_range, delete_user_auth_token, set_user_auth_token


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


class CountryTests(TestCase):
    def test_get_country(self):
        # Countries should be accessible 2 or 3 digit country code
        self.assertEqual(get_country('US'), get_country('USA'))

        # Use common name for Taiwan
        self.assertEqual(get_country('TW').name, 'Taiwan')

        # Return unknown country if code is invalid
        self.assertEqual(get_country('A1'), UNKNOWN_COUNTRY)
        self.assertEqual(get_country(None), UNKNOWN_COUNTRY)


class DateRangeTests(TestCase):
    def test_empty_range(self):
        date = datetime.datetime(2016, 1, 1)
        self.assertEqual([date for date in date_range(date, date)], [])

    def test_range_exclusive(self):
        start_date = datetime.datetime(2016, 1, 1)
        end_date = datetime.datetime(2016, 1, 2)
        self.assertEqual([date for date in date_range(start_date, end_date)], [start_date])

    def test_delta_goes_past_end_date(self):
        start_date = datetime.datetime(2016, 1, 1)
        end_date = datetime.datetime(2016, 1, 3)
        time_delta = datetime.timedelta(days=5)
        self.assertEqual([date for date in date_range(start_date, end_date, time_delta)], [start_date])

    def test_general_range(self):
        start_date = datetime.datetime(2016, 1, 1)
        end_date = datetime.datetime(2016, 1, 5)
        self.assertEqual([date for date in date_range(start_date, end_date)], [
            datetime.datetime(2016, 1, 1),
            datetime.datetime(2016, 1, 2),
            datetime.datetime(2016, 1, 3),
            datetime.datetime(2016, 1, 4),
        ])
