
import logging

import requests
import requests.exceptions


log = logging.getLogger(__name__)


class Client(object):

    """
    A client capable of retrieving the requested resources.

    Return the data for requested resource path in the form of a slash separated relative path. The data is expected to
    be simple python types (dict, list, int, str etc). Higher layers of abstraction are responsible for constructing
    resource paths and interpreting the data structures returned.

    Arguments:

        version (str): When breaking changes are made to either the resource addresses or their returned data, this
            value will change. Multiple clients can be made which adhere to each version.

    """

    # Continue to attempt to retrieve a resource for this many seconds before giving up and raising an error.
    DEFAULT_TIMEOUT = 0.1
    DEFAULT_VERSION = 'v0'

    def __init__(self, version=DEFAULT_VERSION):
        self.version = version

    def get(self, resource, timeout=None):
        """
        Retrieve the data for a resource.

        Arguments:

            resource (str): Path in the form of slash separated strings.

        Raises: ClientError if the resource cannot be retrieved for any reason.

        """
        raise NotImplementedError

    def has_resource(self, resource, timeout=None):
        """
        Check if a resource exists.

        Returns: True iff the resource exists.

        """
        raise NotImplementedError


class RestClient(Client):

    DEFAULT_AUTH_TOKEN = ''
    DEFAULT_BASE_URL = 'http://localhost:9090'

    def __init__(self, base_url=DEFAULT_BASE_URL, auth_token=DEFAULT_AUTH_TOKEN):
        super(RestClient, self).__init__()

        self.base_url = '{0}/api/{1}'.format(base_url, self.version)
        self.auth_token = auth_token

    def get(self, resource, timeout=None):
        response = self._request(resource, timeout=timeout)

        try:
            return response.json()
        except ValueError:
            message = 'Unable to decode JSON response'
            log.exception(message)
            raise ClientError(message)

    def has_resource(self, resource, timeout=None):
        try:
            self._request(resource, timeout=timeout)
            return True
        except ClientError:
            return False

    def _request(self, resource, timeout=None):
        if timeout is None:
            timeout = self.DEFAULT_TIMEOUT

        headers = {
            'Accept': 'application/json',
        }
        if self.auth_token:
            headers['Authorization'] = 'Token ' + self.auth_token

        try:
            response = requests.get('{0}/{1}'.format(self.base_url, resource), headers=headers, timeout=timeout)

            if response.status_code != requests.codes.ok:  # pylint: disable=no-member
                message = 'Resource "{0}" returned status code {1}'.format(resource, response.status_code)
                log.error(message)
                raise ClientError(message)

            return response

        except requests.exceptions.RequestException:
            message = 'Unable to retrieve resource'
            log.exception(message)
            raise ClientError('{0} "{1}"'.format(message, resource))


class ClientError(Exception):
    pass
