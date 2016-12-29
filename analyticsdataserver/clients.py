import logging

from edx_rest_api_client.client import EdxRestApiClient
from edx_rest_api_client.exceptions import HttpClientError
from opaque_keys.edx.keys import UsageKey
from opaque_keys import InvalidKeyError

from analyticsdataserver.utils import temp_log_level

logger = logging.getLogger(__name__)


class CourseBlocksApiClient(EdxRestApiClient):
    """
    This class is a sub-class of the edX Rest API Client
    (https://github.com/edx/edx-rest-api-client).

    Details about the API itself can be found at
    https://openedx.atlassian.net/wiki/display/AN/Course+Structure+API.

    Currently, this client is only used for a local-only developer script (generate_fake_course_data).
    """
    def __init__(self, url, access_token, timeout):
        super(CourseBlocksApiClient, self).__init__(url, oauth_access_token=access_token, timeout=timeout)

    def all_videos(self, course_id):
        try:
            logger.debug('Retrieving course video blocks for course_id: %s', course_id)
            response = self.blocks.get(course_id=course_id, all_blocks=True, depth='all', block_types_filter='video')
            logger.info("Successfully authenticated with the Course Blocks API.")
        except HttpClientError as e:
            if e.response.status_code == 401:
                logger.warning("Course Blocks API failed to return video ids (%s). " +
                               "See README for instructions on how to authenticate the API with your local LMS.",
                               e.response.status_code)
            elif e.response.status_code == 404:
                logger.warning("Course Blocks API failed to return video ids (%s). " +
                               "Does the course exist in the LMS?",
                               e.response.status_code)
            else:
                logger.warning("Course Blocks API failed to return video ids (%s).", e.response.status_code)
            return None

        # Setup a terrible hack to silence mysterious flood of ImportErrors from stevedore inside edx-opaque-keys.
        # (The UsageKey utility still works despite the import errors, so I think the errors are not important).
        with temp_log_level('stevedore', log_level=logging.CRITICAL):
            videos = []
            for video in response['blocks'].values():
                try:
                    encoded_id = UsageKey.from_string(video['id']).html_id()
                except InvalidKeyError:
                    encoded_id = video['id']  # just pass through any wonky ids we don't understand
                videos.append({'video_id': course_id + '|' + encoded_id,
                               'video_module_id': encoded_id})

        return videos
