from __future__ import absolute_import

from datetime import date

from django.test import TestCase

from analytics_data_api.v0 import models as api_models
from analytics_data_api.v0 import serializers as api_serializers
from django_dynamic_fixture import G


class TestSerializer(api_serializers.CourseEnrollmentDailySerializer, api_serializers.DynamicFieldsModelSerializer):
    pass


class DynamicFieldsModelSerializerTests(TestCase):
    def test_fields(self):
        now = date.today()
        instance = G(api_models.CourseEnrollmentDaily, course_id='1', count=1, date=now)
        serialized = TestSerializer(instance)
        self.assertListEqual(list(serialized.data.keys()), ['course_id', 'date', 'count', 'created'])

        instance = G(api_models.CourseEnrollmentDaily, course_id='2', count=1, date=now)
        serialized = TestSerializer(instance, fields=('course_id',))
        self.assertListEqual(list(serialized.data.keys()), ['course_id'])

    def test_exclude(self):
        now = date.today()
        instance = G(api_models.CourseEnrollmentDaily, course_id='3', count=1, date=now)
        serialized = TestSerializer(instance, exclude=('course_id',))
        self.assertListEqual(list(serialized.data.keys()), ['date', 'count', 'created'])
