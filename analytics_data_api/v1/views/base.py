from collections import namedtuple, OrderedDict
from itertools import groupby

from django.core.cache import caches
from django.utils import timezone

from rest_framework import serializers
from opaque_keys.edx.keys import CourseKey

from analytics_data_api.utils import classproperty, join_dicts
from analytics_data_api.v1.exceptions import (
    CourseNotSpecifiedError,
    ParameterValueError,
)
from analytics_data_api.v1.views.utils import (
    split_query_argument,
    validate_course_id,
)


def _get_field(value, field, *args):
    return (
        value.get(field, *args)
        if isinstance(value, dict)
        else getattr(value, field, *args)
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


class TypedQueryParametersAPIViewMixin(object):
    """
    Mixin for collecting parameters in a typed fashion.

    To use, override collect_params. In it, use get_query_param to
    get parameters, and set them as attributes on `self`.

    Example:
    def collect_params(self):
        self.numbers = get_query_params('nums', list, possible_values=set(range(10)))
    """

    def get(self, request, *args, **kwargs):
        # Collect query paramters, and then call superclass's `get`.
        # Returns 422 if any parameter values are rejected.
        # (we don't use a docstring here because it messes with Swagger's UI)
        try:
            self.collect_params()
        except ParameterValueError as e:
            raise serializers.ValidationError(detail=e.message)
        return super(TypedQueryParametersAPIViewMixin, self).get(request, *args, **kwargs)

    def collect_params(self):
        pass

    def get_query_param(self, name, value_type, possible_values=None, none_okay=True):
        """
        Extracts an argument from an HTTP request.

        Arguments:
            name (str): Name of argument
            value_type (type): Expected type of argument value.
                For list, frozenset, and set: JSON value is parsed and converted to type.
                For other types: The type is used as a function that the JSON string is
                    passed directly to. For example, if `int` is passed in, we call
                    `int(<paramter_json_string>)`.
                Note that this may not work for all types. This method may need to be
                modified in the future to support more types.
            possible_values (set|NoneType): Values that are allowed. If None,
                all values are allowed. If value_type is a collection type,
                possible_values refer to allowed elements.
            none_okay: Whether an empty/not-given query paramter is acceptable.

        Returns: value of type value_type

        Raises:
            ParamterValueError: Parameter is wrong type, not in possible_values,
                or None/nonexistent when none_okay=False
        """
        param = self.request.query_params.get(name)
        if param and issubclass(value_type, (list, frozenset, set)):
            param = split_query_argument(param)
        value = value_type(param) if param else None
        return self.validate_query_param(name, value, possible_values, none_okay)

    def has_query_param(self, name):
        return name in self.request.query_params

    @staticmethod
    def validate_query_param(name, value, possible_values, none_okay):
        if none_okay and value is None:
            return value
        value_good = possible_values is None or (
            frozenset(value).issubset(possible_values)
            if isinstance(value, frozenset) or isinstance(value, list)
            else value in possible_values
        )
        if not value_good:
            raise ParameterValueError(
                'Invalid value of {0}: {1}. Expected to be in: {2}'.format(
                    name,
                    value,
                    ', '.join(possible_values)
                )
            )
        return value


class PostAsGetAPIViewMixin(TypedQueryParametersAPIViewMixin):
    """
    Mixin that handles POST requests and treats them as GET requests.

    Provides an interface for getting parameters that is equivalent to
    that of GET requests.
    """
    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_query_param(self, name, value_type, possible_values=None, none_okay=True):
        """
        Overridden from TypedQueryParametersAPIViewMixin.
        """
        if self.request.method == 'GET':
            value = super(PostAsGetAPIViewMixin, self).get_query_param(name, value_type)
        else:
            if issubclass(value_type, (list, frozenset)):
                param = self.request.data.getlist(name)
            else:
                param = self.request.data.get(name)
            value = value_type(param) if param else None
        return self.validate_query_param(name, value, possible_values, none_okay=True)

    def has_query_param(self, name):
        """
        Overridden from TypedQueryParametersAPIViewMixin.
        """
        return (
            super(PostAsGetAPIViewMixin, self).has_query_param(name)
            if self.request.method == 'GET'
            else (name in self.request.data)
        )


class DynamicFieldsAPIViewMixin(TypedQueryParametersAPIViewMixin):
    """
    Mixin for allowing client to blacklist or whitelist response fields.

    `include_param` is used to specify a list of response fields to include.
    `exclude_param` is used to specify a list of response fields to exclude.
    """

    # Optionally override in subclass
    include_param = 'fields'
    exclude_param = 'exclude'

    def __init__(self, *args, **kwargs):
        super(DynamicFieldsAPIViewMixin, self).__init__(*args, **kwargs)
        # We must define these here as None, because we use them
        # in get_serializer_kwargs, which must be available to
        # Swagger.
        self.fields_to_include = None
        self.fields_to_exclude = None

    def collect_params(self):
        """
        Overridden from TypedQueryParametersAPIViewMixin.
        """
        self.fields_to_include = self.get_query_param(self.include_param, frozenset)
        self.fields_to_exclude = self.get_query_param(self.exclude_param, frozenset)
        super(DynamicFieldsAPIViewMixin, self).collect_params()

    def get_serializer(self, *args, **kwargs):
        new_kwargs = join_dicts(
            kwargs,
            self.get_serializer_kwargs(),
            {'context': self.get_serializer_context()},
        )
        return self.get_serializer_class()(*args, **new_kwargs)

    def get_serializer_kwargs(self):
        """
        Overriden from APIView (not in this mixin's hierarchy).
        """
        try:
            super_kwargs = super(DynamicFieldsAPIViewMixin, self).get_serializer_kwargs()
        except AttributeError:
            super_kwargs = {}
        my_kwargs = {
            'fields': (
                list(self.fields_to_include)
                if self.fields_to_include
                else None
            ),
            'exclude': (
                list(self.fields_to_exclude)
                if self.fields_to_exclude
                else None
            ),
        }
        return join_dicts(super_kwargs, my_kwargs)


class IDsAPIViewMixin(TypedQueryParametersAPIViewMixin):
    """
    Mixin for allowing a list of IDs to be passed in as a parameter.
    """

    # Optionally override in superclass
    ids_param = 'ids'

    def collect_params(self):
        """
        Overriden from TypedQueryParmetersAPIViewMixin.
        """
        self.ids = self.get_query_param(self.ids_param, frozenset)
        self.validate_id_formats(self.ids)
        super(IDsAPIViewMixin, self).collect_params()

    @classmethod
    def validate_id_formats(cls, ids):
        """
        In subclass: raise an exception if IDs are malformed.

        Optional to override; by default, does nothing.

        Arguments:
            ids (frozenset[str])

        Raises:
            subclass of Exception: one or IDs are malformed
        """
        pass


class ListAPIViewMixinBase(IDsAPIViewMixin):
    """
    Base mixin for returning a list of processed items.
    """

    def get_queryset(self):
        """
        Overriden from APIView (not in this mixin's inheritance hierarchy)
        """
        return self.process_items(
            (
                self.load_items() if self.ids
                else self.load_all_items()
            )
        ).values()

    def load_items(self):
        """
        Load items, filtered by `self.ids`. Implement in subclass.

        Returns: dict[str: T], where T is item type
            Dictionary from item IDs to items.
        """
        raise NotImplementedError('load_items not implemented in subclass')

    @classmethod
    def load_all_items(cls):
        """
        Load ALL items. Implement in subclass.

        Returns: dict[str: T], where T is item type
            Dictionary from item IDs to items.
        """
        raise NotImplementedError('load_all_items not implemented in subclass')

    def process_items(self, items):
        """
        Process items to be returned in API response.

        Arguments:
            items (dict[str: T]):

        Returns: dict[str: T]

        Note:
            Make sure to call super(...).process_items(items), usually
            before processing the items.
        """
        return items


class ModelListAPIViewMixin(ListAPIViewMixinBase):
    """
    Mixin that implements ListAPIViewMixin by loading items as models from DB.
    """
    # Override in subclass
    model_class = None
    id_field = None

    def load_items(self):
        """
        Overriden from ListAPIViewMixinBase
        """
        return self._group_by_id(
            self.model_class.objects.filter(
                **{self.id_field + '__in': self.ids}
            )
        )

    @classmethod
    def load_all_items(cls):
        """
        Overriden from ListAPIViewMixinBase
        """
        return cls._group_by_id(cls.model_class.objects.all())

    @classmethod
    def _group_by_id(cls, models):
        model_groups = groupby(
            models,
            lambda model: getattr(model, cls.id_field),
        )
        return {
            # We have to use a list comprehension to turn
            # grouper objects into lists...
            model_id: [model for model in model_grouper]
            for model_id, model_grouper in model_groups
        }


# Future TODO: figure out a way to make pylint not complain about
#   no self arguments in @classproperty methods.
# pylint: disable=no-self-argument
class CachedListAPIViewMixin(ListAPIViewMixinBase):
    """
    Mixin that adds caching functionality to a view.
    """

    # Override in subclass
    cache_root_prefix = None
    data_version = None

    # Optionally override in subclass
    cache_name = 'default'
    enable_caching = False

    def load_items(self):
        """
        Overriden from ListAPIViewMixinBase.
        """
        return (
            self._load_cached_items(item_ids=self.ids)
            if self.enable_caching
            else super(CachedListAPIViewMixin, self).load_items()
        )

    @classmethod
    def load_all_items(cls):
        """
        Overriden from ListAPIViewMixinBase.
        """
        return (
            cls._load_cached_items(item_ids=None)
            if cls.enable_caching
            else super(CachedListAPIViewMixin, cls).load_all_items()
        )

    @classmethod
    def _load_cached_items(cls, item_ids=None):
        """
        Try to load items from cache. On failure, fill cache and return items.
        """
        if cls._is_cache_valid():
            item_ids = item_ids or cls.cache.get(cls.cache_item_ids_key)
            if item_ids:
                item_keys_to_load = frozenset(cls.cache_item_key(item_id) for item_id in item_ids)
                items = cls.cache.get_many(item_keys_to_load)
                if item_keys_to_load == frozenset(items.keys()):
                    return items
        all_items_by_id = cls.fill_cache()
        return (
            {
                item_id: all_items_by_id[item_id]
                for item_id in item_ids
                if item_id in all_items_by_id
            }
            if item_ids
            else all_items_by_id
        )

    @classmethod
    def _is_cache_valid(cls):
        cached_data_version = cls.cache.get(cls.cache_data_version_key)
        cached_timestamp = cls.cache.get(cls.cache_timestamp_key)
        return (
            cached_data_version == cls.data_version and
            cached_timestamp >= cls.source_data_timestamp()
        )

    @classmethod
    def source_data_timestamp(cls):
        """
        Get a datetime to store upon filling the cache so the new data can invalidate it.

        Returns: datetime
        """
        raise NotImplementedError('source_data_timestamp not overriden in subclass')

    @classmethod
    def fill_cache(cls):
        all_items_by_id = super(CachedListAPIViewMixin, cls).load_all_items()
        cls.cache.set(cls.cache_data_version_key, cls.data_version, None)
        cls.cache.set(cls.cache_timestamp_key, cls.source_data_timestamp(), None)
        cls.cache.set(cls.cache_item_ids_key, all_items_by_id.keys(), None)
        all_items_by_key = {
            cls.cache_item_key(item_id): item
            for item_id, item in all_items_by_id.iteritems()
        }
        cls.cache.set_many(all_items_by_key, None)
        return all_items_by_id

    @classproperty
    def cache(cls):
        """
        Get cache to use. By default, uses caches[cls.cache_name]
        """
        return caches[cls.cache_name]

    @classproperty
    def cache_data_version_key(cls):
        """
        Get the cache key under which the data version is stored.
        """
        return cls.cache_root_prefix + 'data-version'

    @classproperty
    def cache_timestamp_key(cls):
        """
        Get the cache key under which the timestamp is stored.
        """
        return cls.cache_root_prefix + 'timestamp'

    @classproperty
    def cache_item_ids_key(cls):
        """
        Get the cache key under which the item ID list is stored.
        """
        return cls.cache_root_prefix + 'item-ids'

    @classmethod
    def cache_item_key(cls, item_id):
        """
        Get the cache key under which an item is stored, given its ID.
        """
        return cls.cache_root_prefix + 'items/' + str(item_id)


class AggregatedListAPIViewMixin(ListAPIViewMixinBase):
    """
    Mixin that aggregates loaded items by their IDs.
    """

    # Optionally override in subclass
    basic_aggregate_fields = frozenset()
    calculated_aggregate_fields = {}

    def load_items(self):
        """
        Overrides ListAPIViewMixinBase.
        """
        raw_items = super(AggregatedListAPIViewMixin, self).load_items()
        return self.aggregate(raw_items)

    @classmethod
    def load_all_items(cls):
        """
        Overrides ListAPIViewMixinBase.
        """
        raw_items = super(AggregatedListAPIViewMixin, cls).load_all_items()
        return cls.aggregate(raw_items)

    @classmethod
    def aggregate(cls, raw_item_groups):
        """
        Return results aggregated by a distinct ID.
        """
        return {
            item_id: cls.aggregate_item_group(item_id, raw_item_group)
            for item_id, raw_item_group in raw_item_groups.iteritems()
        }

    @classmethod
    def aggregate_item_group(cls, item_id, raw_item_group):
        """
        Aggregate a group of items. Optionally override in subclass.

        Arguments:
            item_id (str)
            raw_item_group (list[T]), where T is item type

        Returns: U, where U is the aggregate type
        """

        def _apply_or_default(func, val, default):
            return func(val) if val else default

        base = {
            cls.id_field: item_id
        }
        basic = {
            field_name: (
                getattr(raw_item_group[0], field_name, None)
                if raw_item_group else None
            )
            for field_name in cls.basic_aggregate_fields
        }
        calculated = {
            dst_field_name: _apply_or_default(
                func,
                (
                    getattr(raw_item, src_field_name)
                    for raw_item in raw_item_group
                    if hasattr(raw_item, src_field_name)
                ),
                default,
            )
            for dst_field_name, (func, src_field_name, default)
            in cls.calculated_aggregate_fields.iteritems()
        }
        return join_dicts(base, basic, calculated)


# An ad-hoc struct for policies on how to sort
# in SortedListAPIViewMixin
SortPolicy = namedtuple('SortPolicy', 'field default')
SortPolicy.__new__.__defaults__ = (None, None)


# pylint: disable=abstract-method
class SortedListAPIViewMixin(ListAPIViewMixinBase):
    """
    Mixin that adds sorting functionality to a view.
    """

    # Optionally override in subclass
    sort_key_param = 'order_by'
    sort_order_param = 'sort_order'
    sort_policies = {}

    def collect_params(self):
        """
        Overriden from TypedQueryParametersAPIViewMixin.
        """
        self.sort_key = self.get_query_param(
            self.sort_key_param,
            str,
            self.sort_policies.keys()
        )
        self.sort_order = self.get_query_param(
            self.sort_order_param,
            str,
            frozenset(['asc', 'desc']),
        )
        super(SortedListAPIViewMixin, self).collect_params()

    def process_items(self, items):
        """
        Overriden from ListAPIViewMixinBase.
        """
        reverse = (self.sort_order == 'desc')
        return super(SortedListAPIViewMixin, self).process_items(
            OrderedDict(
                sorted(items.iteritems(), key=self._get_sort_value, reverse=reverse)
                if self.sort_key
                else items
            )
        )

    def _get_sort_value(self, item_with_id):
        """
        Given an item, return the key by which it'll be sorted.

        Arguments:
            item_with_id ((str, T)), where T is the item type

        Returns: U, where U is the sort key type
        """
        sort_policy = self.sort_policies[self.sort_key]
        value = item_with_id[1].get(
            sort_policy.field or self.sort_key
        ) or sort_policy.default
        return sort_policy.default if value is None else value


# Ad-hoc struct for policies on how to filter
# in FilteredListAPIViewMixin
FilterPolicy = namedtuple('FilterPolicy', 'field values value_map')
FilterPolicy.__new__.__defaults__ = (None, None, None)


# pylint: disable=abstract-method
class FilteredListAPIViewMixin(ListAPIViewMixinBase):
    """
    Mixin that adds filtering functionality to a view.
    """

    # Optionally override in subclass
    filter_policies = {}

    def collect_params(self):
        """
        Overriden from TypedQueryParametersAPIViewMixin.
        """
        param_filter_values = {
            param_name: (policy, self.get_query_param(
                param_name,
                frozenset,
                policy.value_map.keys() if policy.value_map else policy.values
            ))
            for param_name, policy in self.filter_policies.iteritems()
            if self.has_query_param(param_name)
        }
        self.filters = {
            policy.field or param_name: (
                frozenset.union(*(
                    policy.value_map[value] for value in values
                ))
                if policy.value_map
                else values
            )
            for param_name, (policy, values) in param_filter_values.iteritems()
        }
        super(FilteredListAPIViewMixin, self).collect_params()

    def process_items(self, items):
        """
        Overriden from ListAPIViewMixinBase.
        """
        return super(FilteredListAPIViewMixin, self).process_items(
            OrderedDict(
                (item_id, item)
                for item_id, item in items.iteritems()
                if self._keep_item(item)
            )
            if self.filters
            else items
        )

    def _keep_item(self, item):
        """
        Returns whether or not an item should be kept, as opposed to filtered out.
        """
        for field_name, allowed_values in self.filters.iteritems():
            value = _get_field(item, field_name, None)
            if isinstance(value, (frozenset, set, list)):
                if not bool(frozenset(value) & allowed_values):
                    return False
            else:
                if value not in allowed_values:
                    return False
        return True


# pylint: disable=abstract-method
class SearchedListAPIViewMixin(ListAPIViewMixinBase):
    """
    Mixin that adds searching functionality to a view.
    """

    # Override in subclass
    search_param = None
    search_fields = frozenset()

    def collect_params(self):
        """
        Overriden from TypedQueryParametersAPIViewMixin.
        """
        search = self.get_query_param(self.search_param, str)
        self.search = search.lower() if search else None
        super(SearchedListAPIViewMixin, self).collect_params()

    def process_items(self, items):
        """
        Overriden from ListAPIViewMixinBase.
        """
        return super(SearchedListAPIViewMixin, self).process_items(
            OrderedDict(
                (item_id, item)
                for item_id, item in items.iteritems()
                if self._matches_search(item)
            )
            if self.search
            else items
        )

    def _matches_search(self, item):
        for search_field in self.search_fields:
            # pylint: disable=superfluous-parens
            if self.search in (_get_field(item, search_field, '') or '').lower():
                return True
        return False
