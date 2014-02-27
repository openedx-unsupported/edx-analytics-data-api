from __future__ import absolute_import

from mock import patch, call

from edx.analytics.tasks.mapreduce import MultiOutputMapReduceJobTask
from edx.analytics.tasks.tests import unittest


class MultiOutputMapReduceJobTaskTest(unittest.TestCase):

    def setUp(self):
        self.task = TestJobTask(
            mapreduce_engine='local'
        )

        patcher = patch('edx.analytics.tasks.mapreduce.get_target_from_url')
        self.mock_get_target = patcher.start()
        self.addCleanup(patcher.stop)

    def test_reducer(self):
        self.assert_values_written_to_file('foo', ['bar', 'baz'])

    def assert_values_written_to_file(self, key, values):
        self.assertItemsEqual(self.task.reducer(key, values), [])

        self.mock_get_target.assert_called_once_with('/any/path/' + key)

        mock_target = self.mock_get_target.return_value
        mock_file = mock_target.open.return_value.__enter__.return_value
        mock_file.write.assert_has_calls([ call(v + '\n') for v in values ])

        self.mock_get_target.reset_mock()

    def test_multiple_reducer_calls(self):
        self.assert_values_written_to_file('foo', ['bar', 'baz'])
        self.assert_values_written_to_file('foo2', ['bar2'])


class TestJobTask(MultiOutputMapReduceJobTask):

    def output_path_for_key(self, key):
        return '/any/path/' + key

    def multi_output_reducer(self, key, values, output_file):
        for value in values:
            output_file.write(value + '\n')
