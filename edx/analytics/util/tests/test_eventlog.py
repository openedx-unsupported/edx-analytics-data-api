"""
Tests for utilities that parse event logs.

"""

import unittest

import edx.analytics.util.eventlog as eventlog

class EventLogTest(unittest.TestCase):
    """
    Tests to verify that event log parsing works correctly.
    """

    def test_parse_valid_eventlog_item(self):
        line = '{"username": "successful"}'
        result = eventlog.parse_eventlog_item(line)
        self.assertTrue(isinstance(result, dict))

    def test_parse_eventlog_item_truncated(self):
        line = '{"username": "unsuccessful'
        result = eventlog.parse_eventlog_item(line)
        self.assertIsNone(result)

    def test_parse_eventlog_item_with_cruft(self):
        line = 'leading cruft here {"username": "successful"}  '
        result = eventlog.parse_eventlog_item(line)
        self.assertTrue(isinstance(result, dict))

    def test_parse_eventlog_item_with_nonascii(self):
        line = '{"username": "b\ufffdb"}'
        result = eventlog.parse_eventlog_item(line)
        self.assertTrue(isinstance(result, dict))
        self.assertEquals(result['username'], u'b\ufffdb')


