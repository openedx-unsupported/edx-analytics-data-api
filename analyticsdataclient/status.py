

class Status(object):

    def __init__(self, client):
        self.client = client

    @property
    def alive(self):
        return self.client.has_resource('status')

    @property
    def authenticated(self):
        return self.client.has_resource('authenticated')
