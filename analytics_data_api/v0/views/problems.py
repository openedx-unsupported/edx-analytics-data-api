"""
API methods for module level data.
"""

from itertools import groupby

from rest_framework import generics

from analytics_data_api.v0.models import ProblemResponseAnswerDistribution
from analytics_data_api.v0.serializers import ConsolidatedAnswerDistributionSerializer
from analytics_data_api.v0.models import GradeDistribution
from analytics_data_api.v0.serializers import GradeDistributionSerializer
from analytics_data_api.v0.models import SequentialOpenDistribution
from analytics_data_api.v0.serializers import SequentialOpenDistributionSerializer
from analytics_data_api.utils import consolidate_answers


class ProblemResponseAnswerDistributionView(generics.ListAPIView):
    """
    Get the distribution of student answers to a specific problem.

    **Example request**

        GET /api/v0/problems/{problem_id}/answer_distribution

    **Response Values**

        Returns a collection for each unique answer given to specified
        problem. Each collection contains:

            * course_id: The ID of the course for which data is returned.
            * module_id: The ID of the problem.
            * part_id: The ID for the part of the problem. For multi-part
              problems, a collection is returned for each part.
            * correct: Whether the answer was correct (``true``) or not
              (``false``).
            * count: The number of times the answer in this collection was
              given.
            * value_id: The ID of the answer in this collection.
            * answer_value: An answer for this problem.
            * problem_display_name: The display name for the specified problem.
            * question_text: The question for the specified problem.
            * variant: For randomized problems, the random seed used. If problem
              is not randomized, value is null.
            * created: The date the count was computed.

    **Parameters**

        You can request consolidation of response counts for erroneously randomized problems.

        consolidate_variants -- If True, attempt to consolidate responses, otherwise, do not.

    """

    serializer_class = ConsolidatedAnswerDistributionSerializer
    allow_empty = False

    def get_queryset(self):
        """Select all the answer distribution response having to do with this usage of the problem."""
        problem_id = self.kwargs.get('problem_id')

        queryset = ProblemResponseAnswerDistribution.objects.filter(module_id=problem_id).order_by('part_id')

        consolidated_rows = []

        for _, part in groupby(queryset, lambda x: x.part_id):
            consolidated_rows += consolidate_answers(list(part))

        return consolidated_rows


class GradeDistributionView(generics.ListAPIView):
    """
    Get the distribution of grades for a specific problem.

    **Example request**

        GET /api/v0/problems/{problem_id}/grade_distribution

    **Response Values**

        Returns a collection for each unique grade given to a specified
        problem. Each collection contains:

            * course_id: The ID of the course for which data is returned.
            * module_id: The ID of the problem.
            * grade: The grade being counted in this collection.
            * count: The number of times the grade in this collection was
              given.
            * max_grade: The highest possible grade for this problem.
            * created: The date the count was computed.
    """

    serializer_class = GradeDistributionSerializer
    allow_empty = False

    def get_queryset(self):
        """Select all grade distributions for a particular module"""
        problem_id = self.kwargs.get('problem_id')
        return GradeDistribution.objects.filter(module_id=problem_id)


class SequentialOpenDistributionView(generics.ListAPIView):
    """
    Get the number of views of a subsection, or sequential, in the course.

    **Example request**

        GET /api/v0/problems/{module_id}/sequential_open_distribution

    **Response Values**

        Returns a collection that contains the number of views of the specified
        problem. The collection contains:

            * course_id: The ID of the course for which data is returned.
            * module_id: The ID of the subsection, or sequential.
            * count: The number of times the subsection was viewed.
            * created: The date the count computed.
    """

    serializer_class = SequentialOpenDistributionSerializer
    allow_empty = False

    def get_queryset(self):
        """Select the view count for a specific module"""
        module_id = self.kwargs.get('module_id')
        return SequentialOpenDistribution.objects.filter(module_id=module_id)
