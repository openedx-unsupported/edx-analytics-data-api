import boto
import json
import logging
import os
import subprocess
import sys
if sys.version_info[:2] <= (2, 6):
    import unittest2 as unittest
else:
    import unittest


log = logging.getLogger(__name__)


class AcceptanceTestCase(unittest.TestCase):

    acceptance = 1
    NUM_MAPPERS = 4
    NUM_REDUCERS = 2

    def setUp(self):
        self.s3_conn = boto.connect_s3()

        config_json = os.getenv('ACCEPTANCE_TEST_CONFIG')
        try:
            with open(config_json, 'r') as config_json_file:
                self.config = json.load(config_json_file)
        except (IOError, TypeError):
            try:
                self.config = json.loads(config_json)
            except TypeError:
                self.config = {}

        self.data_dir = os.path.join(os.path.dirname(__file__), 'fixtures')

    def call_subprocess(self, command):
        """Execute a subprocess and log the command before running it."""
        log.info('Running subprocess {0}'.format(command))
        subprocess.check_call(command)
