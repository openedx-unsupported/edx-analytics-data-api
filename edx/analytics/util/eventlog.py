"""Support for reading tracking event logs."""

import sys
import cjson
import datetime
import re


PATTERN_JSON = re.compile(r'^.*?(\{.*\})\s*$')


def get_datetime_string(timestamp):
    return timestamp.strftime('%Y-%m-%dT%H:%M:%S')


def get_date_string(timestamp):
    return timestamp.strftime('%Y-%m-%d')


def get_date_from_datetime(datetime_string):
    return datetime_string.split('T')[0]


def json_decode(line):
    """Wrapper to decode JSON string in implementation-independent way."""
    return cjson.decode(line)


def parse_eventlog_item(line, nested=False):
    """ Parse a tracking log input line as JSON to create a dict representation."""
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
    sys.stderr.write("{level}: {msg}: {item}\n".format(msg=msg, item=item, level=level))


def get_timestamp(item):

    try:
        timestamp = item['time']
        removed_ms = timestamp.split('.')[0]
        return datetime.datetime.strptime(removed_ms, '%Y-%m-%dT%H:%M:%S')
    except:
        return None


def get_event_data(item):
    event_value = item.get('event')

    if event_value is None:
        log_item("encountered event with missing event value", item)
        return None

    if isinstance(event_value, basestring):
        # If the value is a string, try to parse as JSON into a dict:.
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

