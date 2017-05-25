from rest_framework import generics
from analytics_data_api.v0 import models, serializers


class BaseOrgView(generics.ListAPIView):
    org_id = None

    def get(self, request, *args, **kwargs):
        self.org_id = self.kwargs.get('org_id')
        return super(BaseOrgView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.model.objects.filter(org_id=self.org_id)
        return queryset


# pylint: disable=abstract-method
class ProblemsAndTagsListView(BaseOrgView):
    """
    Get the courses and the problems with the connected tags.

    **Example request**

        GET /api/v0/orgs/{org_id}/problems_and_tags/

    **Response Values**

        Returns a collection of submission counts and tags for each problem. Each collection contains:

            * course_id: The ID of the course.
            * module_id: The ID of the problem.
            * total_submissions: Total number of submissions.
            * correct_submissions: Total number of *correct* submissions.
            * tags: Dictionary that contains pairs "tag key: [tag value_1, tag_value_2, ..., tag_value_n]".
    """
    serializer_class = serializers.CoursesProblemsAndTagsSerializer
    allow_empty = False
    model = models.ProblemsAndTags

    def get_queryset(self):
        queryset = self.model.objects.filter(org_id=self.org_id)
        items = queryset.all()

        result = {}

        for v in items:
            if v.module_id in result:
                if v.tag_name not in result[v.module_id]['tags']:
                    result[v.module_id]['tags'][v.tag_name] = []
                result[v.module_id]['tags'][v.tag_name].append(v.tag_value)
                result[v.module_id]['tags'][v.tag_name].sort()
                if result[v.module_id]['created'] < v.created:
                    result[v.module_id]['created'] = v.created
            else:
                result[v.module_id] = {
                    'course_id': v.course_id,
                    'module_id': v.module_id,
                    'total_submissions': v.total_submissions,
                    'correct_submissions': v.correct_submissions,
                    'tags': {
                        v.tag_name: [v.tag_value]
                    },
                    'created': v.created
                }

        return result.values()
