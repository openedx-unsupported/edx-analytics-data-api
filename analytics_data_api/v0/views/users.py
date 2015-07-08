"""
API methods for user data.
"""
from django.http import Http404
from rest_framework import generics

from analytics_data_api.v0.models import UserProfile
from analytics_data_api.v0.serializers import UserProfileSerializer


class UserListView(generics.ListAPIView):
    """
    Get the (paginated) list of all users (students and staff).

    **Example Request**

        GET /api/v0/users/

    **Response Values**

        Returns a collection of user objects. Each user object contains:

            * id: The user's ID (integer)
            * username: The username (string)
            * last_login: When the user last logged in to the LMS/Studio (datetime)
            * date_joined: When the user registered (datetime)
            * is_staff: True if the user is staff (boolean)
            * email: The user's email address (string)
            * name: The user's full name (string)
            * gender: One of "male", "female", "other", or "unknown" (string)
            * year_of_birth: Year of birth as integer or null
            * level_of_education: String indicating self-reported education level, or "unknown"
    """

    serializer_class = UserProfileSerializer

    def get_queryset(self):
        """Select the view count for a specific module"""
        return UserProfile.objects.all()


class UserProfileView(generics.RetrieveAPIView):
    """
    Get the profile data of a user.

    **Example Request**

        GET /api/v0/users/{user_id}/

    **Response Values**

        Returns an object with these properties:

            * id: The user's ID (integer)
            * username: The username (string)
            * last_login: When the user last logged in to the LMS/Studio (datetime)
            * date_joined: When the user registered (datetime)
            * is_staff: True if the user is staff (boolean)
            * email: The user's email address (string)
            * name: The user's full name (string)
            * gender: One of "male", "female", "other", or "unknown" (string)
            * year_of_birth: Year of birth as integer or null
            * level_of_education: String indicating self-reported education level, or "unknown"
    """

    serializer_class = UserProfileSerializer
    lookup_url_kwarg = 'user_id'

    def get_queryset(self):
        """Select the profile of a specific user"""
        try:
            user_id = int(self.kwargs.get('user_id'))
        except ValueError:
            raise Http404
        return UserProfile.objects.filter(pk=user_id)
