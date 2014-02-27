"""
Support executing map reduce tasks.
"""
from __future__ import absolute_import

import luigi
import luigi.hdfs
import luigi.hadoop

from edx.analytics.tasks.url import get_target_from_url, IgnoredTarget


class MapReduceJobTask(luigi.hadoop.JobTask):
    """
    Execute a map reduce job.  Typically using Hadoop, but can execute the
    jobs in process as well.
    """

    mapreduce_engine = luigi.Parameter(
        default_from_config={'section': 'map-reduce', 'name': 'engine'}
    )

    def job_runner(self):
        # Lazily import this since this module will be loaded on hadoop worker nodes however stevedore will not be
        # available in that environment.
        from stevedore import ExtensionManager

        extension_manager = ExtensionManager('mapreduce.engine')
        try:
            engine_class = extension_manager[self.mapreduce_engine].plugin
        except KeyError:
            raise KeyError('A map reduce engine must be specified in order to run MapReduceJobTasks')

        return engine_class()


class MultiOutputMapReduceJobTask(MapReduceJobTask):
    """
    Produces multiple output files from a map reduce job.

    The mapper output tuple key is used to determine the name of the file that reducer results are written to. Different
    reduce tasks must not write to the same file.  Since all values for a given mapper output key are guaranteed to be
    processed by the same reduce task, we only allow a single file to be output per key for safety.  In the future, the
    reducer output key could be used to determine the output file name, however,
    """

    def output(self):
        # Unfortunately, Luigi requires an output.
        return IgnoredTarget()

    def reducer(self, key, values):
        """
        Write out values from each key into different output files.
        """
        output_path = self.output_path_for_key(key)
        if output_path:
            output_file_target = get_target_from_url(output_path)
            with output_file_target.open('w') as output_file:
                self.multi_output_reducer(key, values, output_file)

        # Luigi requires the reducer to return an iterable
        return iter(tuple())

    def multi_output_reducer(self, key, values, output_file):
        """Returns an iterable of strings that are written out to the appropriate output file for this key."""
        return iter(tuple())

    def output_path_for_key(self, key):
        """
        Returns a URL that is unique to the given key.

        All values returned from the reducer for the given key will be output to the file specified by the URL returned
        from this function.
        """
        return None
