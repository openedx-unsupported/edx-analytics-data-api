"""
Tasks for performing encryption on export files.
"""
from contextlib import contextmanager
import logging
import tempfile

import gnupg
import luigi
import yaml

from edx.analytics.tasks.mapreduce import MultiOutputMapReduceJobTask
from edx.analytics.tasks.url import get_target_from_url, url_path_join, ExternalURL
from edx.analytics.tasks.util.tempdir import make_temp_directory

log = logging.getLogger(__name__)


@contextmanager
def make_encrypted_file(output_file, key_file_targets, recipients):
    """Creates a file object to be written to, whose contents will afterwards be encrypted."""
    with make_temp_directory(prefix="encrypt") as temp_dir:
        # Use temp directory to hold gpg keys.
        gpg = gnupg.GPG(gnupghome=temp_dir)
        _import_key_files(gpg, key_file_targets)

        # Create a temp file to contain the unencrypted output, in the same temp directory.
        with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False) as temp_input_file:
            temp_input_filepath = temp_input_file.name
            yield temp_input_file

        # Encryption produces a second file in the same temp directory.
        temp_encrypted_filepath = "{filepath}.gpg".format(filepath=temp_input_filepath)
        with open(temp_input_filepath, 'r') as temp_input_file:
            _encrypt_file(gpg, temp_input_file, temp_encrypted_filepath, recipients)
        _copy_file_to_open_file(temp_encrypted_filepath, output_file)


def _import_key_files(gpg_instance, key_file_targets):
    """
    Load key-file targets into the GPG instance.

    This writes files in the home directory of the instance.
    """
    for key_file_target in key_file_targets:
        log.info("Importing keyfile from %s", key_file_target.path)
        with key_file_target.open('r') as gpg_key_file:
            gpg_instance.import_keys(gpg_key_file.read())


def _encrypt_file(gpg_instance, input_file, encrypted_filepath, recipients):
    """Encrypts a given file open for read, and writes result to a file."""
    gpg_instance.encrypt_file(
        input_file,
        recipients,
        always_trust=True,
        output=encrypted_filepath,
        armor=False,
    )


def _copy_file_to_open_file(filepath, output_file):
    """Copies a filepath to a file object already opened for writing."""
    with open(filepath, 'r') as src_file:
        while True:
            transfer_buffer = src_file.read(1024)
            if transfer_buffer:
                output_file.write(transfer_buffer)
            else:
                break


class FakeEventExportWithEncryptionTask(MultiOutputMapReduceJobTask):
    """Example class to demonstrate use of encryption of files for export from multi-output."""
    source = luigi.Parameter()
    config = luigi.Parameter()
    # TODO: these parameters could be moved into the config file.
    gpg_key_dir = luigi.Parameter()
    gpg_master_key = luigi.Parameter(default=None)

    def init_reducer(self):
        self._get_organization_info()

    def requires(self):
        return {
            'source': ExternalURL(self.source),
            'config': ExternalURL(self.config),
        }

    def requires_local(self):
        return self.requires()['config']

    def requires_hadoop(self):
        return self.requires()['source']

    def mapper(self, line):
        org_id = "edx"
        server_id = "prod-edxapp-011"
        yield (org_id, server_id), line

    def extra_modules(self):
        return [gnupg, yaml]

    def output_path_for_key(self, key):
        org_id, server_id = key
        return url_path_join(self.output_root, org_id, server_id, 'tracking.log.gpg')

    def multi_output_reducer(self, key, values, output_file):
        org_id, _server_id = key
        recipients = self._get_recipients(org_id)
        key_file_targets = [get_target_from_url(url_path_join(self.gpg_key_dir, recipient)) for recipient in recipients]
        with make_encrypted_file(output_file, key_file_targets, recipients) as encrypted_output_file:
            for value in values:
                encrypted_output_file.write(value)
                encrypted_output_file.write('\n')

    def _get_organization_info(self):
        """Get the organization configuration from the configuration yaml file."""
        with self.input()['config'].open() as config_input:
            config_data = yaml.load(config_input)
        self.organizations = config_data['organizations']  # pylint: disable=attribute-defined-outside-init

    def _get_recipients(self, org_id):
        """Get the correct recipients for the specified organization."""
        recipients = [self.organizations[org_id]['recipient']]
        if self.gpg_master_key is not None:
            recipients.append(self.gpg_master_key)
        return recipients
