from django.test import TestCase

from django_dynamic_fixture import G

from analytics_data_api.v0.models import EducationLevel, Country


class EducationLevelTests(TestCase):
    def test_unicode(self):
        short_name = 'high_school'
        name = 'High School'
        education_level = G(EducationLevel, short_name=short_name, name=name)

        self.assertEqual(unicode(education_level), "{0} - {1}".format(short_name, name))


class CountryTests(TestCase):
    def test_unicode(self):
        code = 'US'
        name = 'United States of America'
        country = G(Country, code=code, name=name)

        self.assertEqual(unicode(country), "{0} - {1}".format(code, name))
