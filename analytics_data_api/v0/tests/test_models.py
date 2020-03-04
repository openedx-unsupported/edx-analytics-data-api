from __future__ import absolute_import

from django.test import TestCase

from analytics_data_api.constants.country import UNKNOWN_COUNTRY, get_country
from analytics_data_api.v0 import models
from django_dynamic_fixture import G


class CourseEnrollmentByCountryTests(TestCase):
    def test_country(self):
        country = get_country('US')
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
