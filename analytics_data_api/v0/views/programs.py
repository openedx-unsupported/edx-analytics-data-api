from itertools import groupby

from rest_framework import generics

from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.views.utils import (
    raise_404_if_none,
)


class ProgramsView(generics.ListAPIView):
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
    """
    program_ids = None
    fields = ('program_id', 'program_type', 'program_title')
    serializer_class = serializers.CourseProgramMetadataSerializer
    model = models.CourseProgramMetadata

    def get_serializer(self, *args, **kwargs):
        kwargs.update({
            'context': self.get_serializer_context(),
            'fields': self.fields,
        })
        return self.get_serializer_class()(*args, **kwargs)

    def default_program(self, program_id):
        """Default program with id, empty metadata, and empty courses array."""
        program = {
            'program_id': program_id,
            'program_type': '',
            'program_title': '',
            'created': None,
            'courses': [],
        }
        return program

    def group_by_program(self, queryset):
        """Return enrollment counts for nested in each mode and top-level enrollment counts."""
        formatted_data = []
        for program_id, programs in groupby(queryset, lambda x: (x.program_id)):
            item = self.default_program(program_id)

            # aggregate the program/course pairs to one program item with course_ids array
            for program in programs:
                program_meta_fields = ['program_type', 'program_title']
                item.update({field: getattr(program, field) for field in program_meta_fields})
                item['courses'].append(program.course_id)

                # treat the most recent as the authoritative created date -- should be all the same
                item['created'] = max(program.created, item['created']) if item['created'] else program.created

            formatted_data.append(item)
        return formatted_data

    @raise_404_if_none
    def get_queryset(self):
        queryset = self.model.objects.all()
        programs = self.group_by_program(queryset)
        return programs
