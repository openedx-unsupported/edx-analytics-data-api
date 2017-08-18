from django.core.paginator import InvalidPage

from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination


def _positive_int(integer_string, strict=False, cutoff=None):
    """
    Cast a string to a strictly positive integer.
    """
    ret = int(integer_string)
    if ret < 0 or (ret == 0 and strict):
        raise ValueError()
    if cutoff:
        return min(ret, cutoff)
    return ret


class PostAsGetPaginationBase(PageNumberPagination):

    page_size_query_param = 'page_size'

    # Override in subclass
    page_size = None
    max_page_size = None

    # pylint: disable=attribute-defined-outside-init
    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate a queryset if required, either returning a
        page object, or `None` if pagination is not configured for this view.
        """
        if request.method == 'GET':
            return super(PostAsGetPaginationBase, self).paginate_queryset(
                queryset,
                request,
                view=view
            )

        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = request.data.get(self.page_query_param, 1)
        if page_number in self.last_page_strings:
            page_number = paginator.num_pages

        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=exc.message
            )
            raise NotFound(msg)

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request
        return list(self.page)

    def get_page_size(self, request):
        if request.method == 'GET':
            if self._is_all_in_params(request.query_params):
                return None
            return super(PostAsGetPaginationBase, self).get_page_size(request)

        if self._is_all_in_params(request.data):
            return None
        if self.page_size_query_param and self.page_size_query_param in request.data:
            try:
                return _positive_int(
                    request.data.get(self.page_size_query_param),
                    strict=True,
                    cutoff=self.max_page_size
                )
            except (KeyError, ValueError):
                pass
        return self.page_size

    @staticmethod
    def _is_all_in_params(params):
        param = params.get('all')
        return param and param.lower() == 'true'
