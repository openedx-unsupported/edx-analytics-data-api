from time import time

import jwt
from django.test import TestCase


class JWTSanityTest(TestCase):
    """ Test for the JWT sanity check."""
    def test_encode_decode(self):
        """
        This test ensure  jwt.encode and jwt.decode are working properly.
        """
        now = int(time())
        payload = {
            "iss": 'test-issue',
            "aud": 'test-audience',
            "exp": now + 10,
            "iat": now,
            "username": 'staff',
            "email": 'staff@example.com',
        }
        secret = 'test-secret'
        jwt_message = jwt.encode(payload, secret)
        decoded_payload = jwt.decode(jwt_message, secret, verify=False)

        assert payload == decoded_payload
