from django.test import TestCase

from django_dynamic_fixture import G
from iso3166 import countries

from analytics_data_api.v0 import models


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
