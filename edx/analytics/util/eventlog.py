"""Support for reading tracking event logs."""

import sys
import cjson
import datetime
import re


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
    components = course_id.split('/')
    if len(components) != 3:
        return False
    return all(PATTERN_COURSEID.match(component) for component in components)


def json_decode(line):
    """Wrapper to decode JSON string in an implementation-independent way."""
    return cjson.decode(line)


def parse_eventlog_item(line, nested=False):
    """
    Parse a tracking log input line as JSON to create a dict representation.

    Arguments:
    * line:  the eventlog text
    * nested: boolean flag permitting this to be called recursively.

    Apparently some eventlog entries are pure JSON, while others are
    JSON that are prepended by a timestamp.
    """
    try:
        parsed = json_decode(line)
    except:
        if not nested:
            json_match = PATTERN_JSON.match(line)
            if json_match:
                return parse_eventlog_item(json_match.group(1), nested=True)

        # Seem to be truncated in input data at 10000 for some log files, 2043 for others...
        # First filter out common ones:
        # if 'save_problem_check' not in line:
        #     sys.stderr.write("ERROR: encountered event with bad json: length = {len} start={start}\n".format(len=len(line), start=line[:40]))
        # Even that leaves too many to log.
        # TODO: Might be good going forward to collect stats on the length of truncation and the counts for
        # different event "names" (normalized event_type values).
        return None
    return parsed


def log_item(msg, item, level='ERROR'):
    """Writes a message about an eventlog item."""
    sys.stderr.write("{level}: {msg}: {item}\n".format(msg=msg, item=item, level=level))


# Time-related terminology:
# * datetime: a datetime object.
# * timestamp: a string, with date and time (to second), in ISO format.
# * datestamp: a string with only date information, in ISO format.

def get_timestamp(datetime):
    """Returns a string with the datetime value of the provided datetime object."""
    return datetime.strftime('%Y-%m-%dT%H:%M:%S')


def get_datestamp(datetime):
    """Returns a string with the date value of the provided datetime object."""
    return datetime.strftime('%Y-%m-%d')


def get_datestamp_from_timestamp(timestamp):
    """Returns a string with the date value of the provided ISO datetime string."""
    return timestamp.split('T')[0]


def get_datetime(item):
    """Returns a datetime object from an event item, if present."""
    try:
        timestamp = item['time']
        removed_ms = timestamp.split('.')[0]
        return datetime.datetime.strptime(removed_ms, '%Y-%m-%dT%H:%M:%S')
    except:
        return None


def get_event_data(item):
    """
    Returns event data from an event log item as a dict object.

    Returns None if not found.
    """
    event_value = item.get('event')

    if event_value is None:
        log_item("encountered event with missing event value", item)
        return None

    if isinstance(event_value, basestring):
        # If the value is a string, try to parse as JSON into a dict.
        try:
            event_value = json_decode(event_value)
        except:
            log_item("encountered event with unparsable event value", item)
            return None

    if isinstance(event_value, dict):
        # It's fine, just return.
        return event_value
    else:
        log_item("encountered event data with unrecognized type", item)
        return None

