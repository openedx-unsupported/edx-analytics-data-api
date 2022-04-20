from datetime import date

import ddt
from django.test import TestCase
from django_dynamic_fixture import G

from analytics_data_api.tests.test_utils import set_databases
from analytics_data_api.v0 import models as api_models
from analytics_data_api.v0 import serializers as api_serializers


class TestSerializer(api_serializers.CourseEnrollmentDailySerializer, api_serializers.DynamicFieldsModelSerializer):
    pass


@set_databases
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


@set_databases
@ddt.ddt
class ProblemResponseAnswerDistributionSerializerTests(TestCase):

    @ddt.data(
        ('', ''),
        ('justastring', 'justastring'),
        ('25.94', '25.94'),
        ('[0, 100, 7, "x", "Duōshǎo"]', '[0|100|7|x|Duōshǎo]'),
        ('"a","b" <choicehint>Correct.</choicehint> o', '"a","b" Correct. o'),
        ('[{"3":"t1"},{"2":"t2"}]', '[{"3": "t1"}|{"2": "t2"}]'),
        ('[[1,0,0],[0,1,0],[0,0,1],[0,0,0]]', '[[1, 0, 0]|[0, 1, 0]|[0, 0, 1]|[0, 0, 0]]'),
        ('["<text>(S \\to D \\to G)</text>"]', '[(S \\to D \\to G)]'),
        ('\\((2,1,3)^\\n\\)', '\\((2,1,3)^\\n\\)'),
        (
            'MLE [mathjax]\\widehat{\\theta }_ n^{\\text {MLE}}[/mathjax]',
            'MLE [mathjax]\\widehat{\\theta }_ n^{\\text {MLE}}[/mathjax]'
        ),
        ('<img src="doggo.png" height="100"/>', ''),
        ('<table><tr><td>(0</td><td>1/3</td><td>0)</td></tr></table>', '(0 1/3 0)'),
    )
    @ddt.unpack
    def test_answer_formatting(self, answer_value, expected_display):
        instance = G(
            api_models.ProblemFirstLastResponseAnswerDistribution,
            answer_value=answer_value,
            value_id=answer_value
        )
        serialized = api_serializers.ProblemFirstLastResponseAnswerDistributionSerializer(instance)
        self.assertEqual(serialized.data['answer_value'], expected_display)
        self.assertEqual(serialized.data['value_id'], expected_display)

    @ddt.data(
        ('"hello**ONEBACKSLASHQUOTE**', '"hello\\"'),
        ('**BACKSLASHSPACE**hello', '\\ hello'),
        ('**FOURBACKSLASHQUOTE****TWOBACKSLASHQUOTE**', '\\\\\\\\"\\\\"'),
    )
    @ddt.unpack
    def test_answer_value_unslugged(self, answer_value, expected_display):
        instance = G(api_models.ProblemFirstLastResponseAnswerDistribution, answer_value=answer_value)
        serialized = api_serializers.ProblemFirstLastResponseAnswerDistributionSerializer(instance)
        self.assertEqual(serialized.data['answer_value'], expected_display)
