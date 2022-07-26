"""
API methods for module level data.
"""


import logging

from django.conf import settings
from edx_django_utils.cache import TieredCache, get_cache_key
from enterprise_data.models import EnterpriseUser
from rest_framework import generics

from analytics_data_api.v0.models import ModuleEngagement
from analytics_data_api.v0.serializers import EdxPaginationSerializer, EnterpriseLearnerEngagementSerializer

logger = logging.getLogger(__name__)


class EnterpriseLearnerEngagementView(generics.ListAPIView):
    """
    Return engagement data for enterprise learners.
    """
    serializer_class = EnterpriseLearnerEngagementSerializer
    pagination_class = EdxPaginationSerializer

    @property
    def cached_enterprise_learns(self):
        """
        Caches Enterprise Learns if cache found, else get fresh copy and returns.
        """
        enterprise_id = self.kwargs.get('enterprise_customer')
        cache_key = get_cache_key(
            resource='enterprise_users',
            resource_id=enterprise_id,
        )
        enterprise_users_cache = TieredCache.get_cached_response(cache_key)
        if enterprise_users_cache.is_found:
            return enterprise_users_cache.value

        enterprise_users = list(EnterpriseUser.objects.filter(
            enterprise_id=self.kwargs.get('enterprise_customer')
        ).values_list(
            'user_username', flat=True
        ))
        TieredCache.set_all_tiers(cache_key, enterprise_users, settings.ENGAGEMENT_CACHE_TIMEOUT)
        return enterprise_users

    def get_cached_module_engagement_count(self):
        """
            Caches Module Engagement records count for specific enterprise.
        """
        enterprise_id = self.kwargs.get('enterprise_customer')
        cache_key = get_cache_key(
            resource='module_engagement_count',
            resource_id=enterprise_id,
        )
        module_engagement_count_cache = TieredCache.get_cached_response(cache_key)
        if module_engagement_count_cache.is_found:
            return module_engagement_count_cache.value

        queryset = self._get_queryset()
        count = queryset.count()
        TieredCache.set_all_tiers(cache_key, count, settings.ENGAGEMENT_CACHE_TIMEOUT)
        return count

    def _get_queryset(self):
        """ Return ModuleEngagement queryset"""
        return ModuleEngagement.objects.filter(
            username__in=self.cached_enterprise_learns
        ).exclude(
            entity_type__in=settings.EXCLUDED_ENGAGEMENT_ENTITY_TYPES
        ).order_by('id')

    def get_queryset(self):
        """ Wrapper on the _get_queryset also overrides count method to return cached count."""
        query_set = self._get_queryset()
        setattr(query_set, 'count', self.get_cached_module_engagement_count)
        return query_set
