from rest_framework import generics

from analytics_data_api.v0.models import ProblemResponseAnswerDistribution
from analytics_data_api.v0.serializers import ProblemResponseAnswerDistributionSerializer


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
