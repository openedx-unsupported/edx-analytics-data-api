"""
API methods for user data.
"""
from django.http import Http404
from rest_framework import generics

from analytics_data_api.v0.models import UserProfile
from analytics_data_api.v0.serializers import UserProfileSerializer


class UserProfileView(generics.RetrieveAPIView):
    """
    Get the profile data of a user.

    **Example Request**

        GET /api/v0/users/{user_id}/profile/

    **Response Values**

        See the serializer
    """

    serializer_class = UserProfileSerializer
    allow_empty = False

    def get_queryset(self):
        """Select the view count for a specific module"""
        try:
            user_id = int(self.kwargs.get('pk'))
        except ValueError:
            raise Http404
        return UserProfile.objects.filter(pk=user_id)
