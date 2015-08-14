from django.utils import timezone
from django_dynamic_fixture import G

from analytics_data_api.v0 import models
from analyticsdataserver.tests import TestCaseWithAuthentication


class UsersTests(TestCaseWithAuthentication):

    def _get_data(self, username=None):
        return self.authenticated_get('/api/v0/users/{}/'.format(username))

    def test_get_profile(self):
        date_value = timezone.now()
        G(
            models.UserProfile,
            id=2000,
            username="fred",
            last_login=date_value,
            date_joined=date_value,
            is_staff=False,
            email="fred@example.com",
            name="Fred Loblaw",
            gender_raw="m",
            year_of_birth=1789,
            level_of_education_raw="p",
        )

        expected = {
            "id": 2000,
            "username": "fred",
            "last_login": date_value,
            "date_joined": date_value,
            "is_staff": False,
            "email": "fred@example.com",
            "name": "Fred Loblaw",
            "gender": "male",
            "year_of_birth": 1789,
            "level_of_education": "doctorate"
        }
        response = self._get_data('fred')
        self.assertEquals(response.status_code, 200)
        self.assertEqual(response.data, expected)

    def test_get_profile_404(self):
        response = self._get_data('other')
        self.assertEquals(response.status_code, 404)
