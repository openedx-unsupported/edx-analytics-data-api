
from analyticsdataclient.client import Client, ClientError


class InMemoryClient(Client):

    """Serves resources that have previously been set and stored in memory."""

    def __init__(self):
        """Initialize the fake client."""
        super(InMemoryClient, self).__init__()
        self.resources = {}

    def has_resource(self, resource, timeout=None):
        """Return True iff the resource has been previously set."""
        try:
            self.get(resource, timeout=timeout)
            return True
        except ClientError:
            return False

    def get(self, resource, timeout=None):
        """Return the resource from memory."""
        try:
            return self.resources[resource]
        except KeyError:
            raise ClientError('Unable to find requested resource')
