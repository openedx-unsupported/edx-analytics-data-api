# coding=utf-8
# NOTE: Full URLs are used throughout these tests to ensure that the API contract is fulfilled. The URLs should *not*
# change for versions greater than 1.0.0. Tests target a specific version of the API, additional tests should be added
# for subsequent versions if there are breaking changes introduced in those versions.

# pylint: disable=no-member,no-value-for-parameter

import json

from django_dynamic_fixture import G

from analytics_data_api.v0 import models
from analytics_data_api.v0.serializers import ProblemFirstLastResponseAnswerDistributionSerializer, \
    GradeDistributionSerializer, SequentialOpenDistributionSerializer
from analyticsdataserver.tests import TestCaseWithAuthentication


class AnswerDistributionTests(TestCaseWithAuthentication):
    path = '/answer_distribution/'
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super(AnswerDistributionTests, cls).setUpClass()
        cls.course_id = "org/num/run"
        cls.module_id1 = "i4x://org/num/run/problem/RANDOMNUMBER"
        cls.module_id2 = "i4x://org/num/run/problem/OTHERRANDOM"
        cls.part_id = "i4x-org-num-run-problem-RANDOMNUMBER_2_1"
        cls.correct = True
        cls.value_id1 = '3'
        cls.value_id2 = '4'
        cls.answer_value = '3'
        cls.problem_display_name = 'Test Problem'
        cls.question_text = 'Question Text'

        cls.ad1 = G(
            models.ProblemFirstLastResponseAnswerDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id1,
            part_id=cls.part_id,
            correct=cls.correct,
            value_id=cls.value_id1,
            answer_value=cls.answer_value,
            problem_display_name=cls.problem_display_name,
            question_text=cls.question_text,
            variant=123,
            first_response_count=1,
            last_response_count=3,
        )
        cls.ad2 = G(
            models.ProblemFirstLastResponseAnswerDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id1,
            part_id=cls.part_id,
            correct=cls.correct,
            value_id=cls.value_id1,
            answer_value=cls.answer_value,
            problem_display_name=cls.problem_display_name,
            question_text=cls.question_text,
            variant=345,
            first_reponse_count=0,
            last_response_count=2,
        )
        cls.ad3 = G(
            models.ProblemFirstLastResponseAnswerDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id1,
            part_id=cls.part_id,
        )
        cls.ad4 = G(
            models.ProblemFirstLastResponseAnswerDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id2,
            part_id=cls.part_id,
            value_id=cls.value_id1,
            correct=True,
        )
        cls.ad5 = G(
            models.ProblemFirstLastResponseAnswerDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id2,
            part_id=cls.part_id,
            value_id=cls.value_id2,
            correct=True
        )
        cls.ad6 = G(
            models.ProblemFirstLastResponseAnswerDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id2,
            part_id=cls.part_id,
            value_id=cls.value_id1,
            correct=False,
        )

    def test_nonconsolidated_get(self):
        """ Verify that answers which should not be consolidated are not. """
        response = self.authenticated_get('/api/v0/problems/%s%s' % (self.module_id2, self.path))
        self.assertEquals(response.status_code, 200)

        expected_data = models.ProblemFirstLastResponseAnswerDistribution.objects.filter(module_id=self.module_id2)
        expected_data = [ProblemFirstLastResponseAnswerDistributionSerializer(answer).data for answer in expected_data]

        for answer in expected_data:
            answer['consolidated_variant'] = False

        response.data = set([json.dumps(answer) for answer in response.data])
        expected_data = set([json.dumps(answer) for answer in expected_data])

        self.assertEqual(response.data, expected_data)

    def test_consolidated_get(self):
        """ Verify that valid consolidation does occur. """
        response = self.authenticated_get(
            '/api/v0/problems/{0}{1}'.format(self.module_id1, self.path))
        self.assertEquals(response.status_code, 200)

        expected_data = [self.ad1, self.ad3]

        expected_data[0].first_response_count += self.ad2.first_response_count
        expected_data[0].last_response_count += self.ad2.last_response_count

        expected_data = [ProblemFirstLastResponseAnswerDistributionSerializer(answer).data for answer in expected_data]

        expected_data[0]['variant'] = None
        expected_data[0]['consolidated_variant'] = True

        expected_data[1]['consolidated_variant'] = False

        response.data = [json.dumps(answer) for answer in response.data]
        expected_data = [json.dumps(answer) for answer in expected_data]

        self.assertEquals(set(response.data), set(expected_data))

    def test_get_404(self):
        response = self.authenticated_get('/api/v0/problems/%s%s' % ("DOES-NOT-EXIST", self.path))
        self.assertEquals(response.status_code, 404)


class GradeDistributionTests(TestCaseWithAuthentication):
    path = '/grade_distribution/'
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super(GradeDistributionTests, cls).setUpClass()
        cls.course_id = "org/class/test"
        cls.module_id = "i4x://org/class/test/problem/RANDOM_NUMBER"
        cls.ad1 = G(
            models.GradeDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id,
        )

    def test_get(self):
        response = self.authenticated_get('/api/v0/problems/%s%s' % (self.module_id, self.path))
        self.assertEquals(response.status_code, 200)

        expected_dict = GradeDistributionSerializer(self.ad1).data
        actual_list = response.data
        self.assertEquals(len(actual_list), 1)
        self.assertDictEqual(actual_list[0], expected_dict)

    def test_get_404(self):
        response = self.authenticated_get('/api/v0/problems/%s%s' % ("DOES-NOT-EXIST", self.path))
        self.assertEquals(response.status_code, 404)


class SequentialOpenDistributionTests(TestCaseWithAuthentication):
    path = '/sequential_open_distribution/'
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super(SequentialOpenDistributionTests, cls).setUpClass()
        cls.course_id = "org/class/test"
        cls.module_id = "i4x://org/class/test/problem/RANDOM_NUMBER"
        cls.ad1 = G(
            models.SequentialOpenDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id,
        )

    def test_get(self):
        response = self.authenticated_get('/api/v0/problems/%s%s' % (self.module_id, self.path))
        self.assertEquals(response.status_code, 200)

        expected_dict = SequentialOpenDistributionSerializer(self.ad1).data
        actual_list = response.data
        self.assertEquals(len(actual_list), 1)
        self.assertDictEqual(actual_list[0], expected_dict)

    def test_get_404(self):
        response = self.authenticated_get('/api/v0/problems/%s%s' % ("DOES-NOT-EXIST", self.path))
        self.assertEquals(response.status_code, 404)
