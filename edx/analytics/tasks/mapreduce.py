"""
Support executing map reduce tasks.
"""
from __future__ import absolute_import

import luigi.hadoop

from stevedore import ExtensionManager


class MapReduceJobTask(luigi.hadoop.JobTask):
    """
    Execute a map reduce job.  Typically using Hadoop, but can execute the
    jobs in process as well.
    """

    mapreduce_engine = luigi.Parameter(
        default_from_config={'section': 'map-reduce', 'name': 'engine'}
    )

    def job_runner(self):
        extension_manager = ExtensionManager('mapreduce.engine')
        try:
            engine_class = extension_manager[self.mapreduce_engine].plugin
        except KeyError:
            raise KeyError('A map reduce engine must be specified in order to run MapReduceJobTasks')

        return engine_class()
