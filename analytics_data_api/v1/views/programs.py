from rest_framework.generics import ListAPIView

from analytics_data_api.v1 import models, serializers
from analytics_data_api.v1.views.base import (
    AggregatedListAPIViewMixin,
    DynamicFieldsAPIViewMixin,
    ModelListAPIViewMixin,
)


class ProgramsView(
        AggregatedListAPIViewMixin,
        ModelListAPIViewMixin,
        DynamicFieldsAPIViewMixin,
        ListAPIView,
):
    """
    Returns metadata information for programs.

    **Example Request**

        GET /api/v1/course_programs/?program_ids={program_id},{program_id}

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
    id_field = 'program_id'

    # From ListAPIView
    serializer_class = serializers.CourseProgramMetadataSerializer

    # From ListAPIViewMixinBase
    ids_param = id_field + 's'

    # From ModelListAPIViewMixin
    model_class = models.CourseProgramMetadata
    model_id_field = id_field

    # From AggregatedListAPIViewMixin
    raw_item_id_field = id_field
    aggregate_item_id_field = id_field
    basic_aggregate_fields = frozenset(['program_title', 'program_type'])
    calculated_aggregate_fields = {
        'course_ids': (list, 'course_id', []),
        'created': (max, 'created', None),
    }
