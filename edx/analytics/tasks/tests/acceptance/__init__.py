import boto
import gnupg
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
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

    def decrypt_file(self, encrypted_filename, decrypted_filename, key_filename='insecure_secret.key'):
        """
        Decrypts an encrypted file.

        Arguments:
            encrypted_filename (str): The full path to the PGP encrypted file.
            decrypted_filename (str): The full path of the the file to write the decrypted data to.
            key_filename (str): The name of the key file to use to decrypt the data. It should correspond to one of the
                keys found in the gpg-keys directory.

        """
        gpg_home_dir = tempfile.mkdtemp()
        try:
            gpg = gnupg.GPG(gnupghome=gpg_home_dir)
            gpg.encoding = 'utf-8'
            with open(os.path.join('gpg-keys', key_filename), 'r') as key_file:
                gpg.import_keys(key_file.read())

            with open(encrypted_filename, 'r') as encrypted_file:
                gpg.decrypt_file(encrypted_file, output=decrypted_filename)
        finally:
            shutil.rmtree(gpg_home_dir)
