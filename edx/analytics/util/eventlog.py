"""Support for reading tracking event logs."""

import cjson
import datetime
import re

import logging
logger = logging.getLogger(__name__)

PATTERN_JSON = re.compile(r'^.*?(\{.*\})\s*$')

# borrowed from modulestore/parsers.py:
ALLOWED_ID_CHARS = r'[a-zA-Z0-9_\-~.:]'
PATTERN_COURSEID = re.compile(r'^' + ALLOWED_ID_CHARS + r'+$')


def is_valid_course_id(course_id):
    """
    Determines if a course_id from an event log is possibly legitimate.

    Applies two tests:

    * Course Id can be split into org/coursename/runname using '/' as delimiter.
    * Components of id contain only "allowed" characters as defined in modulestore/parsers.py.

    Note this will need to be updated as split-mongo changes are rolled out
    that permit a broader set of id values.
    """
    # TODO: [split-mongo] verify after course_id name changes.
    components = course_id.split('/')
    if len(components) != 3:
        return False
    return all(PATTERN_COURSEID.match(component) for component in components)


def decode_json(line):
    """Wrapper to decode JSON string in an implementation-independent way."""
    # TODO: Verify correctness of cjson
    return cjson.decode(line)


def parse_json_event(line, nested=False):
    """
    Parse a tracking log input line as JSON to create a dict representation.

    Arguments:
    * line:  the eventlog text
    * nested: boolean flag permitting this to be called recursively.

    Apparently some eventlog entries are pure JSON, while others are
    JSON that are prepended by a timestamp.
    """
    try:
        parsed = decode_json(line)
    except Exception:
        if not nested:
            json_match = PATTERN_JSON.match(line)
            if json_match:
                return parse_json_event(json_match.group(1), nested=True)

        # TODO: There are too many to be logged.  It might be useful
        # at some point to collect stats on the length of truncation
        # and the counts for different event "names" (normalized
        # event_type values).

        # Note that empirically some seem to be truncated in input
        # data at 10000 characters, 2043 for others...
        return None

    # TODO: add basic validation here.

    return parsed


# Time-related terminology:
# * datetime: a datetime object.
# * timestamp: a string, with date and time (to millisecond), in ISO format.
# * datestamp: a string with only date information, in ISO format.

def datetime_to_timestamp(datetime_obj):
    """
    Returns a string with the datetime value of the provided datetime object.

    Note that if the datetime has zero microseconds, the microseconds will not be output.
    """
    return datetime_obj.isoformat()


def datetime_to_datestamp(datetime_obj):
    """Returns a string with the date value of the provided datetime object."""
    return datetime_obj.strftime('%Y-%m-%d')


def timestamp_to_datestamp(timestamp):
    """Returns a string with the date value of the provided ISO datetime string."""
    return timestamp.split('T')[0]


def get_event_time(event):
    """Returns a datetime object from an event object, if present."""
    try:
        # Get entry, and strip off time zone information.  Keep microseconds, if any.
        raw_timestamp = event['time']
        timestamp = raw_timestamp.split('+')[0]
        if '.' not in timestamp:
            timestamp = '{datetime}.000000'.format(datetime=timestamp)
        return datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f')
    except Exception:
        return None


def get_event_data(event):
    """
    Returns event data from an event log entry as a dict object.

    Returns None if not found.
    """
    event_value = event.get('event')

    if event_value is None:
        logger.error("encountered event with missing event value: %s", event)
        return None

    if isinstance(event_value, basestring):
        # If the value is a string, try to parse as JSON into a dict.
        try:
            event_value = decode_json(event_value)
        except Exception:
            logger.error("encountered event with unparsable event value: %s", event)
            return None

    if isinstance(event_value, dict):
        # It's fine, just return.
        return event_value
    else:
        logger.error("encountered event data with unrecognized type: %s", event)
        return None
