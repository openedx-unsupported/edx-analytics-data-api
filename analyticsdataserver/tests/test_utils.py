import logging

from django.test import TestCase

from analyticsdataserver.utils import temp_log_level


class UtilsTests(TestCase):
    def setUp(self):
        self.logger = logging.getLogger('test_logger')

    def test_temp_log_level(self):
        """Ensures log level is adjusted within context manager and returns to original level when exited."""
        original_level = self.logger.getEffectiveLevel()
        with temp_log_level('test_logger'):  # NOTE: defaults to logging.CRITICAL
            self.assertEqual(self.logger.getEffectiveLevel(), logging.CRITICAL)
        self.assertEqual(self.logger.getEffectiveLevel(), original_level)

        # test with log_level option used
        with temp_log_level('test_logger', log_level=logging.DEBUG):
            self.assertEqual(self.logger.getEffectiveLevel(), logging.DEBUG)
        self.assertEqual(self.logger.getEffectiveLevel(), original_level)
