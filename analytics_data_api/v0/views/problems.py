from rest_framework import generics

from analytics_data_api.v0.models import ProblemResponseAnswerDistribution
from analytics_data_api.v0.serializers import ProblemResponseAnswerDistributionSerializer

from analytics_data_api.v0.models import GradeDistribution
from analytics_data_api.v0.serializers import GradeDistributionSerializer

from analytics_data_api.v0.models import SequentialOpenDistribution
from analytics_data_api.v0.serializers import SequentialOpenDistributionSerializer


class ProblemResponseAnswerDistributionView(generics.ListAPIView):
    """
    Distribution of student answers for a particular problem, as used in a particular course.

    Results are available for most (but not all) multiple-choice and short answer response types.
    """

    serializer_class = ProblemResponseAnswerDistributionSerializer
    allow_empty = False

    def get_queryset(self):
        """Select all the answer distribution response having to do with this usage of the problem."""
        problem_id = self.kwargs.get('problem_id')
        return ProblemResponseAnswerDistribution.objects.filter(module_id=problem_id)


class GradeDistributionView(generics.ListAPIView):
    """
    Distribution of grades for a particular module in a given course
    """

    serializer_class = GradeDistributionSerializer
    allow_empty = False

    def get_queryset(self):
        """Select all grade distributions for a particular module"""
        problem_id = self.kwargs.get('problem_id')
        return GradeDistribution.objects.filter(module_id=problem_id)


class SequentialOpenDistributionView(generics.ListAPIView):
    """
    Distribution of view counts for a particular module in a given course
    """

    serializer_class = SequentialOpenDistributionSerializer
    allow_empty = False

    def get_queryset(self):
        """Select the view count for a specific module"""
        module_id = self.kwargs.get('module_id')
        return SequentialOpenDistribution.objects.filter(module_id=module_id)
