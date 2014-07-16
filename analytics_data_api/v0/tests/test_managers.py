from django.core.exceptions import ObjectDoesNotExist

from django.test import TestCase
from django_dynamic_fixture import G

from analytics_data_api.v0.models import Course, Country


class CourseManagerTests(TestCase):
    def test_get_by_natural_key(self):
        course_id = 'edX/DemoX/Demo_Course'
        self.assertRaises(ObjectDoesNotExist, Course.objects.get_by_natural_key, course_id)

        course = G(Course, course_id=course_id)
        self.assertEqual(course, Course.objects.get_by_natural_key(course_id))


class CountryManagerTests(TestCase):
    def test_get_by_natural_key(self):
        code = 'US'
        self.assertRaises(ObjectDoesNotExist, Country.objects.get_by_natural_key, code)

        country = G(Country, code=code)
        self.assertEqual(country, Country.objects.get_by_natural_key(code))
