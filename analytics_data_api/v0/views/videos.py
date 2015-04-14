"""
API methods for module level data.
"""

from rest_framework import generics

from analytics_data_api.v0.models import VideoTimeline
from analytics_data_api.v0.serializers import VideoTimelineSerializer


class VideoTimelineView(generics.ListAPIView):
    """
    Get the timeline for a video.

    **Example request**

        GET /api/v0/videos/{video_id}/timeline/

    **Response Values**

        Returns viewing data for segments of a video.  Each collection contains:

            * segment: Order of the segment in the timeline.
            * num_users: Number of unique users that have viewed this segment.
            * num_views: Number of total views for this segment.
            * created: The date the segment data was computed.
    """

    serializer_class = VideoTimelineSerializer
    allow_empty = False

    def get_queryset(self):
        """Select the view count for a specific module"""
        video_id = self.kwargs.get('video_id')
        return VideoTimeline.objects.filter(pipeline_video_id=video_id)
