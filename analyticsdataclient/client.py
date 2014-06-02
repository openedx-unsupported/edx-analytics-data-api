
import logging

import requests
import requests.exceptions


log = logging.getLogger(__name__)


class Client(object):

    """A client capable of retrieving the requested resources."""

    DEFAULT_TIMEOUT = 0.1  # In seconds
    DEFAULT_VERSION = 'v0'

    def __init__(self, version=DEFAULT_VERSION):
        """
        Initialize the Client.

        Arguments:

            version (str): When breaking changes are made to either the resource addresses or their returned data, this
                value will change. Multiple clients can be made which adhere to each version.

        """
        self.version = version

    def get(self, resource, timeout=None):
        """
        Retrieve the data for a resource.

        Arguments:

            resource (str): Path in the form of slash separated strings.
            timeout (float): Continue to attempt to retrieve a resource for this many seconds before giving up and
                raising an error.

        Returns: A structure consisting of simple python types (dict, list, int, str etc).

        Raises: ClientError if the resource cannot be retrieved for any reason.

        """
        raise NotImplementedError

    def has_resource(self, resource, timeout=None):
        """
        Check if a resource exists.

        Arguments:

            resource (str): Path in the form of slash separated strings.
            timeout (float): Continue to attempt to retrieve a resource for this many seconds before giving up and
                raising an error.

        Returns: True iff the resource exists.

        """
        raise NotImplementedError


class RestClient(Client):

    """Retrieve resources from a remote REST API."""

    DEFAULT_AUTH_TOKEN = ''
    DEFAULT_BASE_URL = 'http://localhost:9090'

    def __init__(self, base_url=DEFAULT_BASE_URL, auth_token=DEFAULT_AUTH_TOKEN):
        """
        Initialize the RestClient.

        Arguments:

            base_url (str): A URL containing the scheme, netloc and port of the remote service.
            auth_token (str): The token that should be used to authenticate requests made to the remote service.

        """
        super(RestClient, self).__init__()

        self.base_url = '{0}/api/{1}'.format(base_url, self.version)
        self.auth_token = auth_token

    def get(self, resource, timeout=None):
        """
        Retrieve the data for a resource.

        Inherited from `Client`.

        Arguments:

            resource (str): Path in the form of slash separated strings.
            timeout (float): Continue to attempt to retrieve a resource for this many seconds before giving up and
                raising an error.

        Returns: A structure consisting of simple python types (dict, list, int, str etc).

        Raises: ClientError if the resource cannot be retrieved for any reason.

        """
        response = self._request(resource, timeout=timeout)

        try:
            return response.json()
        except ValueError:
            message = 'Unable to decode JSON response'
            log.exception(message)
            raise ClientError(message)

    def has_resource(self, resource, timeout=None):
        """
        Check if the server responds with a 200 OK status code when the resource is requested.

        Inherited from `Client`.

        Arguments:

            resource (str): Path in the form of slash separated strings.
            timeout (float): Continue to attempt to retrieve a resource for this many seconds before giving up and
                raising an error.

        Returns: True iff the resource exists.

        """
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


# TODO: Provide more detailed errors as necessary.
class ClientError(Exception):

    """An error occurred that prevented the client from performing the requested operation."""

    pass
