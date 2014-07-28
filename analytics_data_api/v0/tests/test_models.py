from django.test import TestCase

from django_dynamic_fixture import G

from analytics_data_api.v0 import models


class EducationLevelTests(TestCase):
    def test_unicode(self):
        short_name = 'high_school'
        name = 'High School'
        education_level = G(models.EducationLevel, short_name=short_name,
                            name=name)

        self.assertEqual(unicode(education_level),
                         "{0} - {1}".format(short_name, name))


class CountryTests(TestCase):
    # pylint: disable=no-member
    def test_attributes(self):
        country = models.Country('Canada', 'CA')
        self.assertEqual(country.code, 'CA')
        self.assertEqual(country.name, 'Canada')


class CourseEnrollmentByCountryTests(TestCase):
    def test_country(self):
        country = models.Country('United States', 'US')
        instance = G(models.CourseEnrollmentByCountry,
                     country_code=country.code)
        self.assertEqual(instance.country, country)
