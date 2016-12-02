from opaque_keys.edx.keys import CourseKey

from django.utils import timezone
from analytics_data_api.v0.exceptions import CourseNotSpecifiedError
import analytics_data_api.utils as utils


class CourseViewMixin(object):
    """
    Captures the course_id from the url and validates it.
    """

    course_id = None

    def get(self, request, *args, **kwargs):
        self.course_id = self.kwargs.get('course_id', request.query_params.get('course_id', None))

        if not self.course_id:
            raise CourseNotSpecifiedError()
        utils.validate_course_id(self.course_id)
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
