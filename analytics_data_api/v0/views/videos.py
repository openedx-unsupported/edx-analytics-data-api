"""
API methods for module level data.
"""

from rest_framework import generics

from analytics_data_api.v0.models import VideoTimeline
from analytics_data_api.v0.serializers import VideoTimelineSerializer

from utils import raise_404_if_none

class VideoTimelineView(generics.ListAPIView):
    """
    Get the counts of users and views for a video.

    **Example Request**

        GET /api/v0/videos/{video_id}/timeline/

    **Response Values**

        Returns viewing data for each segment of a video.  For each segment,
        the collection contains the following data.

            * segment: The order of the segment in the video timeline.
            * num_users: The number of unique users who viewed this segment.
            * num_views: The number of views for this segment.
            * created: The date the segment data was computed.
    """

    serializer_class = VideoTimelineSerializer
    allow_empty = False

    @raise_404_if_none
    def get_queryset(self):
        """Select the view count for a specific module"""
        video_id = self.kwargs.get('video_id')
        return VideoTimeline.objects.filter(pipeline_video_id=video_id)
