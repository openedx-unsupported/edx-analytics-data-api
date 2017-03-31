from itertools import groupby

from django.db.models import Q

from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.views import APIListView
from analytics_data_api.v0.views.utils import (
    split_query_argument,
)


class ProgramsView(APIListView):
    """
    Returns metadata information for programs.

    **Example Request**

        GET /api/v0/course_programs/?program_ids={program_id},{program_id}

    **Response Values**

        Returns metadata for every program:

            * program_id: The ID of the program for which data is returned.
            * program_type: The type of the program
            * program_title: The title of the program
            * created: The date the counts were computed.

    **Parameters**

        Results can be filed to the course IDs specified or limited to the fields.

        program_ids -- The comma-separated program identifiers for which metadata is requested.
            Default is to return all programs.
        fields -- The comma-separated fields to return in the response.
            For example, 'program_id,created'.  Default is to return all fields.
        exclude -- The comma-separated fields to exclude in the response.
            For example, 'course_id,created'.  Default is to not exclude any fields.
    """
    always_exclude = ['course_id']  # original model has course_id, but the serializer does not (after aggregation)
    serializer_class = serializers.CourseProgramMetadataSerializer
    model = models.CourseProgramMetadata
    model_id = 'program_id'
    program_meta_fields = ['program_type', 'program_title']

    def default_result(self, id):
        """Default program with id, empty metadata, and empty courses array."""
        program = {
            'program_id': id,
            'program_type': '',
            'program_title': '',
            'created': None,
            'courses': [],
        }
        return program

    def get_result_from_model(self, model, base_result=None):
        result = super(ProgramsView, self).get_result_from_model(model, base_result=base_result,
                                                                 field_list=self.program_meta_fields)
        result['courses'].append(model.course_id)

        # treat the most recent as the authoritative created date -- should be all the same
        result['created'] = max(model.created, result['created']) if result['created'] else model.created

        return result

    def get_query(self):
        return reduce(lambda q, id: q | Q(program_id=id), self.ids, Q())
