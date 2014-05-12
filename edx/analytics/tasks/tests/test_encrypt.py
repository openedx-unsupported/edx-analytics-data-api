"""Tests of utilities to encrypt files."""

import gnupg
import tempfile

from edx.analytics.tasks.encrypt import make_encrypted_file, _import_key_files
from edx.analytics.tasks.tests import unittest
from edx.analytics.tasks.url import get_target_from_url
from edx.analytics.tasks.url import url_path_join
from edx.analytics.tasks.util.tempdir import make_temp_directory


class MakeEncryptedFileTest(unittest.TestCase):
    """Test make_encrypted_file context manager."""

    def get_decrypted_data(self, input_file, key_file_target):
        """Decrypts contents of input, and writes to output file object open for writing."""
        with make_temp_directory(prefix="decrypt") as temp_dir:
            # Use temp directory to hold gpg keys.
            gpg_instance = gnupg.GPG(gnupghome=temp_dir)
            _import_key_files(gpg_instance, [key_file_target])
            decrypted_data = gpg_instance.decrypt_file(input_file, always_trust=True)
            return decrypted_data

    def test_make_encrypted_file(self):
        recipient = 'daemon@edx.org'
        gpg_key_dir = 'gpg-keys'
        key_file_targets = [get_target_from_url(url_path_join(gpg_key_dir, recipient))]
        values = ['this', 'is', 'a', 'test']
        with tempfile.NamedTemporaryFile() as output_file:
            with make_encrypted_file(output_file, key_file_targets, [recipient]) as encrypted_output_file:
                for value in values:
                    encrypted_output_file.write(value)
                    encrypted_output_file.write('\n')

            output_file.seek(0)

            # Decrypt the file and compare.
            recipient_private_key = 'insecure_secret.key'
            key_file_target = get_target_from_url(url_path_join(gpg_key_dir, recipient_private_key))
            decrypted_data = self.get_decrypted_data(output_file, key_file_target)
            self.assertEquals(values, str(decrypted_data).strip().split('\n'))
