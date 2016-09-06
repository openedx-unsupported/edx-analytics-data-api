"""
Custom REST framework renderers common to all versions of the API.
"""
from rest_framework_csv.renderers import CSVRenderer
from ordered_set import OrderedSet


class ResultsOnlyRendererMixin(object):
    """
    Render data using just the results array.

    Use with PaginatedHeadersMixin to preserve the pagination links in the response header.
    """
    results_field = 'results'

    def render(self, data, *args, **kwargs):
        """
        Replace the rendered data with just what is in the results_field.
        """
        if not isinstance(data, list):
            data = data.get(self.results_field, [])
        return super(ResultsOnlyRendererMixin, self).render(data, *args, **kwargs)


class DynamicFieldsCsvRenderer(CSVRenderer):
    """
    Allows the `fields` query parameter to determine which fields should be
    returned in the response, and in what order.

    Note that if no header is provided, and the fields_param query string
    parameter is not found in the request, the fields are rendered in
    alphabetical order.
    """
    # Name of the query string parameter to check for the fields list
    # Set to None to ensure that any request fields will not override
    fields_param = 'fields'

    # Seperator character(s) to split the fields parameter list
    fields_sep = ','

    # Set to None to flatten lists into one heading per value.
    # Otherwise, concatenate lists delimiting with the given string.
    concatenate_lists_sep = ', '

    def flatten_list(self, l):
        if self.concatenate_lists_sep is None:
            return super(DynamicFieldsCsvRenderer, self).flatten_list(l)
        return {'': self.concatenate_lists_sep.join(l)}

    def get_header(self, data, renderer_context):
        """Return the list of header fields, determined by class settings and context."""

        # Start with the previously-set list of header fields
        header = renderer_context.get('header', self.header)

        # If no previous set, then determine the candidates from the data
        if header is None:
            header = set()
            data = self.flatten_data(data)
            for item in data:
                header.update(list(item.keys()))

            # Alphabetize header fields by default, since
            # flatten_data() makes field order indeterminate.
            header = sorted(header)

        # If configured to, examine the query parameters for the requsted header fields
        request = renderer_context.get('request')
        if request is not None and self.fields_param is not None:

            request_fields = request.query_params.get(self.fields_param)
            if request_fields is not None:

                requested = OrderedSet()
                for request_field in request_fields.split(self.fields_sep):

                    # Only fields in the original candidate header set are valid
                    if request_field in header:
                        requested.update((request_field,))

                header = requested  # pylint: disable=redefined-variable-type

        return header

    def render(self, data, media_type=None, renderer_context=None, writer_opts=None):
        """Override the default "get headers" behaviour, then render the data."""
        renderer_context = renderer_context or {}
        self.header = self.get_header(data, renderer_context)
        return super(DynamicFieldsCsvRenderer, self).render(data, media_type, renderer_context, writer_opts)


class PaginatedCsvRenderer(ResultsOnlyRendererMixin, DynamicFieldsCsvRenderer):
    """
    Render results-only CSV data with dynamically-determined fields.
    """
    media_type = 'text/csv'
