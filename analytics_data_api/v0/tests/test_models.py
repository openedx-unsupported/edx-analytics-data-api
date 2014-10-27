from django.test import TestCase
from django_dynamic_fixture import G
from iso3166 import countries

from analytics_data_api.v0 import models
from analytics_data_api.constants.country import UNKNOWN_COUNTRY


class EducationLevelTests(TestCase):
    def test_unicode(self):
        short_name = 'high_school'
        name = 'High School'
        education_level = G(models.EducationLevel, short_name=short_name,
                            name=name)

        self.assertEqual(unicode(education_level),
                         "{0} - {1}".format(short_name, name))


class CourseEnrollmentByCountryTests(TestCase):
    def test_country(self):
        country = countries.get('US')
        self.assertEqual(country.alpha2, 'US')
        instance = G(models.CourseEnrollmentByCountry, country_code=country.alpha2)
        self.assertEqual(instance.country, country)

    def test_invalid_country(self):
        instance = G(models.CourseEnrollmentByCountry, country_code='')
        self.assertEqual(instance.country, UNKNOWN_COUNTRY)

        instance = G(models.CourseEnrollmentByCountry, country_code='A1')
        self.assertEqual(instance.country, UNKNOWN_COUNTRY)

        instance = G(models.CourseEnrollmentByCountry, country_code='GobbledyGoop!')
        self.assertEqual(instance.country, UNKNOWN_COUNTRY)

        instance = G(models.CourseEnrollmentByCountry, country_code='UNKNOWN')
        self.assertEqual(instance.country, UNKNOWN_COUNTRY)
