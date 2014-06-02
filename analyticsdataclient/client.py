
import logging

import requests
import requests.exceptions

from analyticsdataclient.status import Status


log = logging.getLogger(__name__)


class Client(object):

    def __init__(self):
        self.status = Status(self)

    def get(self, resource, timeout=None):
        raise NotImplementedError

    def has_resource(self, resource, timeout=None):
        raise NotImplementedError


class RestClient(Client):

    def __init__(self, base_url='http://localhost:9090', auth_token=''):
        super(RestClient, self).__init__()

        self.base_url = base_url + '/api/v0'
        self.auth_token = auth_token

    def get(self, resource, timeout=None):
        response = self.request(resource, timeout=timeout)

        try:
            return response.json()
        except ValueError:
            message = 'Unable to decode JSON response'
            log.exception(message)
            raise ClientError(message)

    def has_resource(self, resource, timeout=None):
        try:
            self.request(resource, timeout=timeout)
            return True
        except ClientError:
            return False

    def request(self, resource, timeout=None):
        if timeout is None:
            timeout = 0.1

        headers = {
            'Accept': 'application/json',
        }
        if self.auth_token:
            headers['Authorization'] = 'Token ' + self.auth_token

        try:
            response = requests.get('{0}/{1}'.format(self.base_url, resource), headers=headers, timeout=timeout)

            if response.status_code != requests.codes.ok:
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
