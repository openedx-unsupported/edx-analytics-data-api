# Put utilities that are used in managing the server or local environment here.
# Utilities critical to application functionality should go under analytics_data_api.
import logging
from contextlib import contextmanager


@contextmanager
def temp_log_level(logger_name, log_level=logging.CRITICAL):
    """
    A context manager that temporarily adjusts a logger's log level.

    By default, log_level is logging.CRITICAL, which will effectively silence the logger while the context
    manager is active.
    """
    logger = logging.getLogger(logger_name)
    original_log_level = logger.getEffectiveLevel()
    logger.setLevel(log_level)  # silences all logs up to but not including this level
    yield
    # Return log level back to what it was.
    logger.setLevel(original_log_level)
