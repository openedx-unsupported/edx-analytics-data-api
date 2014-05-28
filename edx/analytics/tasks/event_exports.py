"""Group events by institution and export them for research purposes"""

import logging
import os

import gnupg
import luigi
import yaml

from edx.analytics.tasks.encrypt import make_encrypted_file
from edx.analytics.tasks.mapreduce import MultiOutputMapReduceJobTask
from edx.analytics.tasks.pathutil import EventLogSelectionTask
from edx.analytics.tasks.url import url_path_join, ExternalURL, get_target_from_url
from edx.analytics.tasks.util import eventlog


log = logging.getLogger(__name__)


class EventExportTask(MultiOutputMapReduceJobTask):
    """
    Group events by institution and export them for research purposes.

    Parameters:
        output_root: Directory to store the output in.
        config: A URL to a YAML file that contains the list of organizations and servers to export events for.
        source: A URL to a path that contains log files that contain the events.
        environment: A list of short strings that describe the environment that generated the events. Only include
            events from this list of environments.
        interval: The range of dates to export logs for.
        pattern: A regex with a named capture group for the date that approximates the date that the events within were
            emitted. Note that the search interval is expanded, so events don't have to be in exactly the right file
            in order for them to be processed.
    """

    output_root = luigi.Parameter(
        default_from_config={'section': 'event-export', 'name': 'output_root'}
    )
    config = luigi.Parameter(
        default_from_config={'section': 'event-export', 'name': 'config'}
    )
    source = luigi.Parameter(
        default_from_config={'section': 'event-logs', 'name': 'source'}
    )
    environment = luigi.Parameter(is_list=True, default=['prod', 'edge'])
    interval = luigi.DateIntervalParameter()
    pattern = luigi.Parameter(default=None)

    gpg_key_dir = luigi.Parameter(
        default_from_config={'section': 'event-export', 'name': 'gpg_key_dir'}
    )
    gpg_master_key = luigi.Parameter(
        default_from_config={'section': 'event-export', 'name': 'gpg_master_key'}
    )

    def requires(self):
        tasks = []
        for env in self.environment:
            tasks.append(
                EventLogSelectionTask(
                    source=self.source,
                    environment=env,
                    interval=self.interval,
                    pattern=self.pattern,
                )
            )
        return tasks

    def requires_local(self):
        return ExternalURL(url=self.config)

    def extra_modules(self):
        return [gnupg, yaml]

    def init_local(self):
        with self.input_local().open() as config_input:
            config_data = yaml.load(config_input)
            self.organizations = config_data['organizations']

        # Map org_ids to recipient names, taking in to account org_id aliases. For example, if an org_id Foo is also
        # known as FooX then two entries will appear in this dictionary ('Foo', 'recipient@foo.org') and
        # ('FooX', 'recipient@foo.org'). Note that both aliases map to the same recipient.
        self.recipient_for_org_id = {}
        for org_id, org_config in self.organizations.iteritems():
            recipient = org_config['recipient']
            self.recipient_for_org_id[org_id] = recipient
            for alias in org_config.get('other_names', []):
                self.recipient_for_org_id[alias] = recipient

        self.org_id_whitelist = self.recipient_for_org_id.keys()
        log.debug('Using org_id whitelist ["%s"]', '", "'.join(self.org_id_whitelist))

        self.server_name_whitelist = set()
        for env in self.environment:
            server_list = config_data.get('environments', {}).get(env, {}).get('servers', [])
            self.server_name_whitelist.update(server_list)

        log.debug('Using server_id whitelist ["%s"]', '", "'.join(self.server_name_whitelist))

        self.lower_bound_date_string = self.interval.date_a.strftime('%Y-%m-%d')
        self.upper_bound_date_string = self.interval.date_b.strftime('%Y-%m-%d')

    def mapper(self, line):
        event = eventlog.parse_json_event(line)
        if event is None:
            return

        try:
            event_time = event['time']
        except KeyError:
            self.incr_counter('Event', 'Missing Time Field', 1)
            return

        # Don't use strptime to parse the date, it is extremely slow to do so. Instead rely on alphanumeric comparisons.
        # The timestamp is ISO8601 formatted, so dates will look like %Y-%m-%d.  For example: 2014-05-20.
        date_string = event_time.split("T")[0]

        if date_string < self.lower_bound_date_string or date_string >= self.upper_bound_date_string:
            return

        org_id = self.get_org_id(event)
        if org_id not in self.org_id_whitelist:
            log.debug('Unrecognized organization: org_id=%s', org_id or '')
            return

        server_id = self.get_server_id()
        if server_id not in self.server_name_whitelist:
            log.debug('Unrecognized server: server_id=%s', server_id or '')
            return

        key = (date_string, org_id, server_id)
        # Enforce a standard encoding for the parts of the key. Without this a part of the key might appear differently
        # in the key string when it is coerced to a string by luigi. For example, if the same org_id appears in two
        # different records, one as a str() type and the other a unicode() then without this change they would appear as
        # u'FooX' and 'FooX' in the final key string. Although python doesn't care about this difference, hadoop does,
        # and will bucket the values separately. Which is not what we want.
        yield tuple([value.encode('utf8') for value in key]), line.strip()

    def get_server_id(self):
        """
        Attempt to determine the server the event was emitted from.

        This method may return incorrect results, so a white list of valid server names is used to filter out the noise.
        """
        try:
            # Hadoop sets an environment variable with the full URL of the input file. This url will be something like:
            # s3://bucket/root/host1/tracking.log.gz. In this example, assume self.source is "s3://bucket/root".
            input_file_name = os.environ['map_input_file']
        except KeyError:
            log.warn('map_input_file not defined in os.environ, unable to determine server_id')
            return None

        # Even if len(self.source) > len(input_file_name) the slice will return ''
        # lstrip is a noop on an empty string
        relative_path = input_file_name[len(self.source):].lstrip('/')
        # relative_path = "host1/tracking.log.gz"

        # Assume the server name is the first directory in the relative path
        path_elements = relative_path.split('/')

        # The result of string.split() always is a list with at least one element
        server = path_elements[0]
        # server = "host1"

        return server

    # This is copied verbatim (only comments changed) from the legacy event log export script.
    def get_org_id(self, item):
        """
        Attempt to determine the institution that is associated with this particular event.

        This method may return incorrect results, so a white list of valid institution names is used to filter out the
        noise.
        """
        try:
            if item['event_source'] == 'server':
                institution = item.get('context', {}).get('org_id')
                if institution:
                    return institution

                # Try to infer the institution from the event data
                evt_type = item['event_type']
                if '/courses/' in evt_type:
                    institution = evt_type.split('/')[2]
                    return institution
                elif '/' in evt_type:
                    return "Global"
                else:
                    # Specific server logging. One-off parser for each type Survey of logs showed 4 event types:
                    # reset_problem save_problem_check, save_problem_check_fail, save_problem_fail All four of these
                    # have a problem_id, which we extract from.
                    try:
                        return item['event']['problem_id'].split('/')[2]
                    except Exception:  # pylint: disable=broad-except
                        return "Unhandled"
            elif item['event_source'] == 'browser':
                page = item['page']
                if 'courses' in page:
                    institution = page.split('/')[4]
                    return institution
                else:
                    return "BGE"
        except Exception:  # pylint: disable=broad-except
            log.exception('Unable to determine institution for event: %s', unicode(item).encode('utf8'))
            return "Exception"

    def output_path_for_key(self, key):
        date, org_id, server_id = key

        # This is the structure currently produced by the existing tracking log export script
        return url_path_join(
            self.output_root,
            org_id,
            server_id,
            '{date}_{org}.log.gpg'.format(
                date=date,
                org=org_id,
            )
        )

    def multi_output_reducer(self, key, values, output_file):
        _date_string, org_id, _server_id = key
        recipients = self._get_recipients(org_id)
        key_file_targets = [get_target_from_url(url_path_join(self.gpg_key_dir, recipient)) for recipient in recipients]
        with make_encrypted_file(output_file, key_file_targets) as encrypted_output_file:
            for value in values:
                encrypted_output_file.write(value.strip())
                encrypted_output_file.write('\n')

    def _get_recipients(self, org_id):
        """Get the correct recipients for the specified organization."""
        recipients = [self.recipient_for_org_id[org_id]]
        if self.gpg_master_key is not None:
            recipients.append(self.gpg_master_key)
        return recipients
