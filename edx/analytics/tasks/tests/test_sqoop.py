"""Tests for Sqoop import task."""

import textwrap

from mock import MagicMock
from mock import patch
from mock import sentinel

from edx.analytics.tasks.sqoop import SqoopImportFromMysql
from edx.analytics.tasks.tests import unittest
from edx.analytics.tasks.tests.target import FakeTarget


class SqoopImportFromMysqlTestCase(unittest.TestCase):
    """
    Ensure we can pass the right arguments to Sqoop.
    """

    def setUp(self):
        patcher = patch('luigi.hdfs.HdfsTarget')
        self.mock_hdfstarget = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_hdfstarget().path = "/temp/password_file"

        patcher2 = patch("luigi.hadoop.run_and_track_hadoop_job")
        self.mock_run = patcher2.start()
        self.addCleanup(patcher2.stop)

    def run_task(self, credentials=None, num_mappers=None, where=None, verbose=False):
        """
        Emulate execution of a generic MysqlTask.
        """
        if not credentials:
            credentials = '''\
                {
                    "host": "db.example.com",
                    "port": "3306",
                    "username": "exampleuser",
                    "password": "example password",
                    "database": "exampledata"
                }'''

        task = SqoopImportFromMysql(
            credentials=sentinel.ignored,
            destination="/fake/destination",
            table_name="example_table",
            num_mappers=num_mappers,
            where=where,
            verbose=verbose
        )

        fake_input = {
            'credentials': FakeTarget(textwrap.dedent(credentials))
        }
        task.input = MagicMock(return_value=fake_input)

        task.run()

        arglist = self.mock_run.call_args[0][0]
        return arglist

    def test_connect_with_missing_credentials(self):
        with self.assertRaises(KeyError):
            self.run_task('{}')
        self.assertTrue(self.mock_hdfstarget().remove.called)
        self.assertFalse(self.mock_run.called)

    def test_connect_with_credential_syntax_error(self):
        with self.assertRaises(ValueError):
            self.run_task('{')
        self.assertTrue(self.mock_hdfstarget().remove.called)
        self.assertFalse(self.mock_run.called)

    def test_connect_with_complete_credentials(self):
        arglist = self.run_task()
        self.assertTrue(self.mock_run.called)
        expected_arglist = [
            'sqoop',
            'import',
            '--connect',
            'jdbc:mysql://db.example.com/exampledata',
            '--username',
            'exampleuser',
            '--password-file',
            '/temp/password_file',
            '--table',
            'example_table',
            '--warehouse-dir',
            '/fake/destination',
            '--direct',
            '--mysql-delimiters'
        ]
        self.assertEquals(arglist, expected_arglist)
        self.assertTrue(self.mock_hdfstarget().remove.called)

    def test_verbose_arguments(self):
        arglist = self.run_task(verbose=True)
        self.assertIn('--verbose', arglist)

    def test_connect_with_where_args(self):
        arglist = self.run_task(where='id < 50')
        self.assertEquals(arglist[-4], '--where')
        self.assertEquals(arglist[-3], 'id < 50')

    def test_connect_with_num_mappers(self):
        arglist = self.run_task(num_mappers=50)
        self.assertEquals(arglist[-4], '--num-mappers')
        self.assertEquals(arglist[-3], '50')
