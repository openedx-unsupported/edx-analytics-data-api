import luigi
import luigi.hdfs

from edx.analytics.tasks.s3 import S3Sync


class SyncEventLogs(luigi.Task):
    """
    Copies the gzipped raw event logs to a new location.

    The directory structure of the source is preserved.

    The parameters will default to the values set in the Luigi
    configuration.

    Parameters:

    `source`: root S3 with raw event logs
    `destination`: root S3 path the events will be copied
    `include`: list of glob expressions of the keys to include.

    """
    source = luigi.Parameter(
        default_from_config={'section': 'event-logs', 'name': 'source'}
    )

    destination = luigi.Parameter(
        default_from_config={'section': 'event-logs', 'name': 'destination'}
    )

    include = luigi.Parameter(
        default_from_config={'section': 'event-logs', 'name': 'include'},
        is_list=True
    )

    def requires(self):
        return S3Sync(self.source, self.destination, self.include)

    def output(self):
        for output in self.requires().output():
            yield luigi.hdfs.HdfsTarget(output.path)
