from django.test import TestCase
from django_dynamic_fixture import G

from analytics_data_api.constants.country import UNKNOWN_COUNTRY, get_country
from analytics_data_api.tests.test_utils import set_databases
from analytics_data_api.v0 import models
from analytics_data_api.v0.models import BaseCourseModel


@set_databases
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


class BaseCourseModelTests(TestCase):
    def test_courseid_key(self):
        course = BaseCourseModel()
        course.course_id = 'course-v1:etsx+Toeflss+2t2019'
        other_course = BaseCourseModel()
        for other in (
                'course-v1:etsx+TOEFLSS+2t2019',
                'course-v1:etsx+toeflss+2t2019',
                'course-v1:etsx+toeflß+2t2019'
        ):
            other_course.course_id = other
            self.assertNotEqual(course.course_id, other_course.course_id, other)
            self.assertEqual(course.course_id_key(), other_course.course_id_key(), other)
            