from django.db.models import Q

from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.views import APIListView


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
            * created: The date the metadata was computed.

    **Parameters**

        Results can be filtered to the program IDs specified or limited to the fields.

        program_ids -- The comma-separated program identifiers for which metadata is requested.
            Default is to return all programs.
        fields -- The comma-separated fields to return in the response.
            For example, 'program_id,created'.  Default is to return all fields.
        exclude -- The comma-separated fields to exclude in the response.
            For example, 'program_id,created'.  Default is to not exclude any fields.
    """
    serializer_class = serializers.CourseProgramMetadataSerializer
    model = models.CourseProgramMetadata
    model_id_field = 'program_id'
    ids_param = 'program_ids'
    program_meta_fields = ['program_type', 'program_title']

    def base_field_dict(self, program_id):
        """Default program with id, empty metadata, and empty courses array."""
        program = super(ProgramsView, self).base_field_dict(program_id)
        program.update({
            'program_type': '',
            'program_title': '',
            'created': None,
            'course_ids': [],
        })
        return program

    def update_field_dict_from_model(self, model, base_field_dict=None, field_list=None):
        field_dict = super(ProgramsView, self).update_field_dict_from_model(model, base_field_dict=base_field_dict,
                                                                            field_list=self.program_meta_fields)
        field_dict['course_ids'].append(model.course_id)

        # treat the most recent as the authoritative created date -- should be all the same
        field_dict['created'] = max(model.created, field_dict['created']) if field_dict['created'] else model.created

        return field_dict

    def get_query(self):
        return reduce(lambda q, item_id: q | Q(program_id=item_id), self.ids, Q())
