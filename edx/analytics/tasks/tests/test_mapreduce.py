"""Tests for classes defined in mapreduce.py."""

from __future__ import absolute_import

from mock import patch, call
import os
import tempfile
import shutil

from edx.analytics.tasks.mapreduce import MultiOutputMapReduceJobTask
from edx.analytics.tasks.tests import unittest


class MultiOutputMapReduceJobTaskTest(unittest.TestCase):
    """Tests for MultiOutputMapReduceJobTask."""

    def setUp(self):
        patcher = patch('edx.analytics.tasks.mapreduce.get_target_from_url')
        self.mock_get_target = patcher.start()
        self.addCleanup(patcher.stop)

        self.task = TestJobTask(
            mapreduce_engine='local',
            output_root='/any/path',
        )

    def test_reducer(self):
        self.assert_values_written_to_file('foo', ['bar', 'baz'])

    def assert_values_written_to_file(self, key, values):
        """Confirm that values passed to reducer appear in output file."""
        self.assertItemsEqual(self.task.reducer(key, values), [])

        self.mock_get_target.assert_called_once_with('/any/path/' + key)

        mock_target = self.mock_get_target.return_value
        mock_file = mock_target.open.return_value.__enter__.return_value
        mock_file.write.assert_has_calls([call(v + '\n') for v in values])

        self.mock_get_target.reset_mock()

    def test_multiple_reducer_calls(self):
        self.assert_values_written_to_file('foo', ['bar', 'baz'])
        self.assert_values_written_to_file('foo2', ['bar2'])


class MultiOutputMapReduceJobTaskOutputRootTest(unittest.TestCase):
    """Tests for output_root behavior of MultiOutputMapReduceJobTask."""

    def setUp(self):
        # Define a real output directory, so it can
        # be removed if existing.
        def cleanup(dirname):
            """Remove the temp directory only if it exists."""
            if os.path.exists(dirname):
                shutil.rmtree(dirname)

        self.output_root = tempfile.mkdtemp()
        self.addCleanup(cleanup, self.output_root)

    def test_no_delete_output_root(self):
        self.assertTrue(os.path.exists(self.output_root))
        TestJobTask(
            mapreduce_engine='local',
            output_root=self.output_root,
        )
        self.assertTrue(os.path.exists(self.output_root))

    def test_delete_output_root(self):
        # We create a task in order to get the output path.
        task = TestJobTask(
            mapreduce_engine='local',
            output_root=self.output_root,
        )
        output_marker = task.output().path
        open(output_marker, 'a').close()
        self.assertTrue(task.complete())

        # Once the output path is created, we can
        # then confirm that it gets cleaned up..
        task = TestJobTask(
            mapreduce_engine='local',
            output_root=self.output_root,
            delete_output_root="true",
        )
        self.assertFalse(task.complete())
        self.assertFalse(os.path.exists(self.output_root))


class TestJobTask(MultiOutputMapReduceJobTask):
    """Dummy task to use for testing."""

    def output_path_for_key(self, key):
        return os.path.join(self.output_root, key)

    def multi_output_reducer(self, key, values, output_file):
        for value in values:
            output_file.write(value + '\n')
