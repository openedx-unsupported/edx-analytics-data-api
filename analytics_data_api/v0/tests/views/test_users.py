from django.utils import timezone
from django_dynamic_fixture import G

from analytics_data_api.v0 import models
from analyticsdataserver.tests import TestCaseWithAuthentication


class UsersTests(TestCaseWithAuthentication):

    def _get_data(self, user_id=None):
        return self.authenticated_get('/api/v0/users/{}/'.format(user_id))

    def test_get_list(self):
        date_value = timezone.now()
        G(
            models.UserProfile,
            id=2000,
            username="bob",
            last_login=date_value,
            date_joined=date_value,
            email="bob@example.com",
            name="Bob Loblaw",
            year_of_birth=1789,
        )
        G(
            models.UserProfile,
            id=2001,
            username="alexa",
            last_login=date_value,
            date_joined=date_value,
            email="alexa@example.com",
            name="Alexa Anderson",
            gender_raw="f",
            year_of_birth=1987,
        )

        expected = [
            {
                "id": 2000,
                "username": "bob",
                "last_login": date_value,
                "date_joined": date_value,
                "is_staff": False,
                "email": "bob@example.com",
                "name": "Bob Loblaw",
                "gender": "unknown",
                "year_of_birth": 1789,
                "level_of_education": "unknown"
            },
            {
                "id": 2001,
                "username": "alexa",
                "last_login": date_value,
                "date_joined": date_value,
                "is_staff": False,
                "email": "alexa@example.com",
                "name": "Alexa Anderson",
                "gender": "female",
                "year_of_birth": 1987,
                "level_of_education": "unknown"
            },
        ]
        response = self.authenticated_get('/api/v0/users/')
        self.assertEquals(response.status_code, 200)
        self.assertListEqual(response.data, expected)

    def test_get_profile(self):
        date_value = timezone.now()
        G(
            models.UserProfile,
            id=2000,
            username="bob",
            last_login=date_value,
            date_joined=date_value,
            is_staff=False,
            email="bob@example.com",
            name="Bob Loblaw",
            gender_raw="m",
            year_of_birth=1789,
            level_of_education_raw="p",
        )

        expected = {
            "id": 2000,
            "username": "bob",
            "last_login": date_value,
            "date_joined": date_value,
            "is_staff": False,
            "email": "bob@example.com",
            "name": "Bob Loblaw",
            "gender": "male",
            "year_of_birth": 1789,
            "level_of_education": "doctorate"
        }
        response = self._get_data(2000)
        self.assertEquals(response.status_code, 200)
        self.assertEqual(response.data, expected)

    def test_get_profile_404(self):
        response = self._get_data('no_id')
        self.assertEquals(response.status_code, 404)
