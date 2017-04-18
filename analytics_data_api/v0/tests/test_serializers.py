from datetime import date
from django.test import TestCase
from django_dynamic_fixture import G

from analytics_data_api.v0 import models as api_models, serializers as api_serializers


class TestSerializer(api_serializers.CourseEnrollmentDailySerializer, api_serializers.DynamicFieldsModelSerializer):
    pass


class DynamicFieldsModelSerializerTests(TestCase):
    def test_fields(self):
        now = date.today()
        instance = G(api_models.CourseEnrollmentDaily, course_id='1', count=1, date=now)
        serialized = TestSerializer(instance)
        self.assertListEqual(serialized.data.keys(), ['course_id', 'date', 'count', 'created'])

        instance = G(api_models.CourseEnrollmentDaily, course_id='2', count=1, date=now)
        serialized = TestSerializer(instance, fields=('course_id',))
        self.assertListEqual(serialized.data.keys(), ['course_id'])

    def test_exclude(self):
        now = date.today()
        instance = G(api_models.CourseEnrollmentDaily, course_id='3', count=1, date=now)
        serialized = TestSerializer(instance, exclude=('course_id',))
        self.assertListEqual(serialized.data.keys(), ['date', 'count', 'created'])
