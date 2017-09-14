from itertools import groupby

from django.db import models
from django.db.models import Q
from django.utils import timezone

from rest_framework import generics, serializers

from opaque_keys.edx.keys import CourseKey

from analytics_data_api.v0.exceptions import CourseNotSpecifiedError
from analytics_data_api.v0.views.utils import (
    raise_404_if_none,
    split_query_argument,
    validate_course_id
)


class CourseViewMixin(object):
    """
    Captures the course_id from the url and validates it.
    """

    course_id = None

    def get(self, request, *args, **kwargs):
        self.course_id = self.kwargs.get('course_id', request.query_params.get('course_id', None))

        if not self.course_id:
            raise CourseNotSpecifiedError()
        validate_course_id(self.course_id)
        return super(CourseViewMixin, self).get(request, *args, **kwargs)


class PaginatedHeadersMixin(object):
    """
    If the response is paginated, then augment it with this response header:

    * Link: list of next and previous pagination URLs, e.g.
        <next_url>; rel="next", <previous_url>; rel="prev"

    Format follows the github API convention:
        https://developer.github.com/guides/traversing-with-pagination/

    Useful with PaginatedCsvRenderer, so that previous/next links aren't lost when returning CSV data.

    """
    # TODO: When we upgrade to Django REST API v3.1, define a custom DEFAULT_PAGINATION_CLASS
    # instead of using this mechanism:
    #   http://www.django-rest-framework.org/api-guide/pagination/#header-based-pagination

    def get(self, request, *args, **kwargs):
        """
        Stores pagination links in a response header.
        """
        response = super(PaginatedHeadersMixin, self).get(request, args, kwargs)
        link = self.get_paginated_links(response.data)
        if link:
            response['Link'] = link
        return response

    @staticmethod
    def get_paginated_links(data):
        """
        Returns the links string.
        """
        # Un-paginated data is returned as a list, not a dict.
        next_url = None
        prev_url = None
        if isinstance(data, dict):
            next_url = data.get('next')
            prev_url = data.get('previous')

        if next_url is not None and prev_url is not None:
            link = '<{next_url}>; rel="next", <{prev_url}>; rel="prev"'
        elif next_url is not None:
            link = '<{next_url}>; rel="next"'
        elif prev_url is not None:
            link = '<{prev_url}>; rel="prev"'
        else:
            link = ''

        return link.format(next_url=next_url, prev_url=prev_url)


class CsvViewMixin(object):
    """
    Augments a text/csv response with this header:

    * Content-Disposition: allows the client to download the response as a file attachment.
    """
    # Default filename slug for CSV download files
    filename_slug = 'report'

    def get_csv_filename(self):
        """
        Returns the filename for the CSV download.
        """
        course_key = CourseKey.from_string(self.course_id)
        course_id = u'-'.join([course_key.org, course_key.course, course_key.run])
        now = timezone.now().replace(microsecond=0)
        return u'{0}--{1}--{2}.csv'.format(course_id, now.isoformat(), self.filename_slug)

    def finalize_response(self, request, response, *args, **kwargs):
        """
        Append Content-Disposition header to CSV requests.
        """
        if request.META.get('HTTP_ACCEPT') == u'text/csv':
            response['Content-Disposition'] = u'attachment; filename={}'.format(self.get_csv_filename())
        return super(CsvViewMixin, self).finalize_response(request, response, *args, **kwargs)


class APIListView(generics.ListAPIView):
    """
    An abstract view to store common code for views that return a list of data.

    **Example Requests**

        GET /api/v0/some_endpoint/
            Returns full list of serialized models with all default fields.

        GET /api/v0/some_endpoint/?ids={id_1},{id_2}
            Returns list of serialized models with IDs that match an ID in the given
            `ids` query parameter with all default fields.

        GET /api/v0/some_endpoint/?ids={id_1},{id_2}&fields={some_field_1},{some_field_2}
            Returns list of serialized models with IDs that match an ID in the given
            `ids` query parameter with only the fields in the given `fields` query parameter.

        GET /api/v0/some_endpoint/?ids={id_1},{id_2}&exclude={some_field_1},{some_field_2}
            Returns list of serialized models with IDs that match an ID in the given
            `ids` query parameter with all fields except those in the given `exclude` query
            parameter.

        POST /api/v0/some_endpoint/
        {
            "ids": [
                "{id_1}",
                "{id_2}",
                ...
                "{id_200}"
            ],
            "fields": [
                "{some_field_1}",
                "{some_field_2}"
            ]
        }

    **Response Values**

        Since this is an abstract class, this view just returns an empty list.

    **Parameters**

        This view supports filtering the results by a given list of IDs. It also supports
        explicitly specifying the fields to include in each result with `fields` as well of
        the fields to exclude with `exclude`.

        For GET requests, these parameters are passed in the query string.
        For POST requests, these parameters are passed as a JSON dict in the request body.

        ids -- The comma-separated list of identifiers for which results are filtered to.
            For example, 'edX/DemoX/Demo_Course,course-v1:edX+DemoX+Demo_2016'. Default is to
            return all courses.
        fields -- The comma-separated fields to return in the response.
            For example, 'course_id,created'. Default is to return all fields.
        exclude -- The comma-separated fields to exclude in the response.
            For example, 'course_id,created'. Default is to not exclude any fields.

    **Notes**

        * GET is usable when the number of IDs is relatively low
        * POST is required when the number of course IDs would cause the URL to be too long.
        * POST functions the same as GET here. It does not modify any state.
    """
    ids = None
    fields = None
    exclude = None
    always_exclude = []
    model_id_field = 'id'
    ids_param = 'ids'

    def get_serializer(self, *args, **kwargs):
        kwargs.update({
            'context': self.get_serializer_context(),
            'fields': self.fields,
            'exclude': self.exclude
        })
        return self.get_serializer_class()(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        query_params = self.request.query_params
        self.fields = split_query_argument(query_params.get('fields'))
        exclude = split_query_argument(query_params.get('exclude'))
        self.exclude = self.always_exclude + (exclude if exclude else [])
        self.ids = split_query_argument(query_params.get(self.ids_param))
        self.verify_ids()

        return super(APIListView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # self.request.data is a QueryDict. For keys with singleton lists as values,
        # QueryDicts return the singleton element of the list instead of the list itself,
        # which is undesirable. So, we convert to a normal dict.
        request_data_dict = dict(request.data)
        self.fields = request_data_dict.get('fields')
        exclude = request_data_dict.get('exclude')
        self.exclude = self.always_exclude + (exclude if exclude else [])
        self.ids = request_data_dict.get(self.ids_param)
        self.verify_ids()

        return super(APIListView, self).get(request, *args, **kwargs)

    def verify_ids(self):
        """
        Optionally raise an exception if any of the IDs set as self.ids are invalid.
        By default, no verification is done.
        Subclasses can override this if they wish to perform verification.
        """
        pass

    def base_field_dict(self, item_id):
        """Default result with fields pre-populated to default values."""
        field_dict = {
            self.model_id_field: item_id,
        }
        return field_dict

    def update_field_dict_from_model(self, model, base_field_dict=None, field_list=None):
        field_list = (field_list if field_list else
                      [f.name for f in self.model._meta.get_fields()])  # pylint: disable=protected-access
        field_dict = base_field_dict if base_field_dict else {}
        field_dict.update({field: getattr(model, field) for field in field_list})
        return field_dict

    def postprocess_field_dict(self, field_dict):
        """Applies some business logic to final result without access to any data from the original model."""
        return field_dict

    def group_by_id(self, queryset):
        """Return results aggregated by a distinct ID."""
        aggregate_field_dict = []
        for item_id, model_group in groupby(queryset, lambda x: (getattr(x, self.model_id_field))):
            field_dict = self.base_field_dict(item_id)

            for model in model_group:
                field_dict = self.update_field_dict_from_model(model, base_field_dict=field_dict)

            field_dict = self.postprocess_field_dict(field_dict)
            aggregate_field_dict.append(field_dict)

        return aggregate_field_dict

    def get_query(self):
        return reduce(lambda q, item_id: q | Q(id=item_id), self.ids, Q())

    @raise_404_if_none
    def get_queryset(self):
        if self.ids:
            queryset = self.model.objects.filter(self.get_query())
        else:
            queryset = self.model.objects.all()

        field_dict = self.group_by_id(queryset)

        # Django-rest-framework will serialize this dictionary to a JSON response
        return field_dict
