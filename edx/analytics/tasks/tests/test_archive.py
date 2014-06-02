"""Tests of utilities to archive files."""

import os
import shutil
import tempfile
import tarfile

import luigi.configuration
import luigi.worker
import yaml

from edx.analytics.tasks.archive import ArchiveExportTask
from edx.analytics.tasks.tests import unittest

# Define test data.
SERVERS = ['prod-edge-edxapp-001', 'prod-edxapp-011']
DATES = ['2014-05-09', '2014-05-10']
TEST_ORGS = {
    'edX': ['edX'],
    'HSchoolX': ['HSchoolX', 'HKSchool', 'HSchool'],
}


class ArchiveExportTaskTestCase(unittest.TestCase):
    """Tests of ArchiveExportTask."""

    def setUp(self):
        # Set up temporary root directory that will get cleaned up.
        def cleanup(dirname):
            """Remove the temp directory only if it exists."""
            if os.path.exists(dirname):
                shutil.rmtree(dirname)

        self.temp_rootdir = tempfile.mkdtemp()
        self.addCleanup(cleanup, self.temp_rootdir)

        # Set up input and output directories.  Define but don't create
        # the output directories.
        self.src_path = os.path.join(self.temp_rootdir, "src")
        os.mkdir(self.src_path)
        self.output_root_path = os.path.join(self.temp_rootdir, "output")
        self.archive_temp_path = os.path.join(self.temp_rootdir, "temp")

    def _create_config_file(self):
        """
        Create a .yaml file that contains organization data in form used by exports.

        Assumes that organization names are in mixed-case, not all-lowercase.
        """
        config_filepath = os.path.join(self.temp_rootdir, "config.yaml")
        org_data = {'organizations': {}}
        for org_name in TEST_ORGS:
            org_dict = {'recipient': "person@{org}.org".format(org=org_name.lower())}
            others = [org for org in TEST_ORGS[org_name] if org != org_name]
            if others:
                org_dict['other_names'] = others
            org_data['organizations'][org_name] = org_dict

        with open(config_filepath, 'w') as config_file:
            yaml.dump(org_data, config_file)
        return config_filepath

    def _create_file_contents(self, org, server, log_date):
        """Create file contents specific to a given org, server, and log date."""
        return "This log was written for {org} on {server} on {date}\n".format(org=org, server=server, date=log_date)

    def _create_input_data(self, src_path, orgs=None):
        """Create tar files in the input directory."""
        if orgs is None:
            orgs = TEST_ORGS
        for org_key in orgs:
            for org in orgs[org_key]:
                org_dir = os.path.join(src_path, org)
                os.mkdir(org_dir)
                for server in SERVERS:
                    server_dir = os.path.join(org_dir, server)
                    os.mkdir(server_dir)
                    for log_date in DATES:
                        log_filepath = os.path.join(server_dir, "{date}_{org}.log".format(date=log_date, org=org))
                        with open(log_filepath, 'w') as log_file:
                            log_file.write(self._create_file_contents(org, server, log_date))

    def _parse_log_file_name(self, logfile_name):
        """
        Extract parameters from log file name.

        Expects name of form "HSchoolX/prod-edge-edxapp-001/2014-05-09_HSchoolX.log".
        """
        org_dir, server, name = logfile_name.split('/')
        date, org = name.split('_')
        org = org[:-4]
        self.assertEquals(org_dir, org)
        return org, server, date

    def _check_tar_file_contents(self, tarfile_path):
        """Confirm that tar file contains the expected input."""
        self.assertTrue(tarfile.is_tarfile(tarfile_path))
        org_name = tarfile_path.split('-')[3]
        self.assertIn(org_name, TEST_ORGS)
        tar_file = tarfile.open(tarfile_path)
        for member_info in tar_file.getmembers():
            org, server, log_date = self._parse_log_file_name(member_info.name)
            member_file = tar_file.extractfile(member_info)
            actual = member_file.read()
            self.assertIn(org, TEST_ORGS[org_name])
            self.assertEquals(actual, self._create_file_contents(org, server, log_date))
        tar_file.close()

    def _run_task(self, config_filepath, **kwargs):
        """Define and run ArchiveExportTask locally in Luigi."""
        # Define and run the task.
        task = ArchiveExportTask(
            mapreduce_engine='local',
            config=config_filepath,
            eventlog_output_root=self.src_path,
            output_root=self.output_root_path,
            temp_dir=self.archive_temp_path,
            **kwargs
        )
        worker = luigi.worker.Worker()
        worker.add(task)
        worker.run()
        worker.stop()

    def test_normal_task(self):
        self._create_input_data(self.src_path)
        config_filepath = self._create_config_file()

        self._run_task(config_filepath)

        # Confirm that the temp directory was created as needed, but was left empty.
        self.assertTrue(os.path.isdir(self.archive_temp_path))
        self.assertEquals(os.listdir(self.archive_temp_path), [])

        # Confirm that the job succeeded.
        output_files = os.listdir(self.output_root_path)

        # Confirm that the output files were correctly tarred.
        for output_file in output_files:
            tarfile_path = os.path.join(self.output_root_path, output_file)
            self._check_tar_file_contents(tarfile_path)

    def test_orgs_with_wrong_case(self):
        # Create data for orgs that differ only by case.
        test_orgs = {
            'HSchoolX': ['HSchoolx', 'HSchoolX'],
        }
        self._create_input_data(self.src_path, orgs=test_orgs)
        config_filepath = self._create_config_file()

        self._run_task(config_filepath)

        # Confirm that output files were tarred for only
        # one of the test orgs (even though the config file
        # contained more).
        output_files = os.listdir(self.output_root_path)
        self.assertEquals(len(output_files), 1)
        output_file = output_files[0]
        tarfile_path = os.path.join(self.output_root_path, output_file)
        self._check_tar_file_contents(tarfile_path)
        tar_file = tarfile.open(tarfile_path)
        self.assertEquals(len(tar_file.getmembers()), len(SERVERS) * len(DATES))
        tar_file.close()

    def test_limited_orgs(self):
        self._create_input_data(self.src_path)
        config_filepath = self._create_config_file()

        self._run_task(config_filepath, org_id=['edX'])

        # Confirm that the job succeeded.
        output_files = os.listdir(self.output_root_path)

        self.assertEquals(len(output_files), 1)
        output_file = output_files[0]

        self.assertEquals(output_file.split('-')[3], 'edX')

        # Confirm that the output files were correctly tarred.
        tarfile_path = os.path.join(self.output_root_path, output_file)
        self._check_tar_file_contents(tarfile_path)
