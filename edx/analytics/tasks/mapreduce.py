"""
Support executing map reduce tasks.
"""
from __future__ import absolute_import

import luigi
import luigi.hdfs
import luigi.hadoop
from luigi import configuration

from edx.analytics.tasks.url import get_target_from_url, url_path_join


# Name of marker file to appear in output directory of MultiOutputMapReduceJobTask to indicate success.
MARKER_FILENAME = 'job_success'


class MapReduceJobTask(luigi.hadoop.JobTask):
    """
    Execute a map reduce job.  Typically using Hadoop, but can execute the
    jobs in process as well.
    """

    mapreduce_engine = luigi.Parameter(
        default_from_config={'section': 'map-reduce', 'name': 'engine'}
    )
    input_format = luigi.Parameter(default=None)
    lib_jar = luigi.Parameter(is_list=True, default=[])

    # Override the parent class definition of this parameter. This typically wants to scale with the cluster size so the
    # user should be able to tweak it depending on their particular configuration.
    n_reduce_tasks = luigi.Parameter(default=25)

    def job_runner(self):
        # Lazily import this since this module will be loaded on hadoop worker nodes however stevedore will not be
        # available in that environment.
        from stevedore import ExtensionManager

        extension_manager = ExtensionManager('mapreduce.engine')
        try:
            engine_class = extension_manager[self.mapreduce_engine].plugin
        except KeyError:
            raise KeyError('A map reduce engine must be specified in order to run MapReduceJobTasks')

        if issubclass(engine_class, MapReduceJobRunner):
            return engine_class(libjars_in_hdfs=self.lib_jar, input_format=self.input_format)
        else:
            return engine_class()


class MapReduceJobRunner(luigi.hadoop.HadoopJobRunner):
    """
    Support more customization of the streaming command.

    Args:
        libjars_in_hdfs (list): An optional list of library jars that the hadoop job can make use of.
        input_format (str): An optional full class name of a hadoop input format to use.
    """

    def __init__(self, libjars_in_hdfs=None, input_format=None):
        libjars_in_hdfs = libjars_in_hdfs or []
        config = configuration.get_config()
        streaming_jar = config.get('hadoop', 'streaming-jar')

        super(MapReduceJobRunner, self).__init__(
            streaming_jar,
            input_format=input_format,
            libjars_in_hdfs=libjars_in_hdfs
        )


class MultiOutputMapReduceJobTask(MapReduceJobTask):
    """
    Produces multiple output files from a map reduce job.

    The mapper output tuple key is used to determine the name of the file that reducer results are written to. Different
    reduce tasks must not write to the same file.  Since all values for a given mapper output key are guaranteed to be
    processed by the same reduce task, we only allow a single file to be output per key for safety.  In the future, the
    reducer output key could be used to determine the output file name, however,

    Parameters:
        output_root: a URL location where the split files will be stored.
        delete_output_root: if True, recursively deletes the output_root at task creation.
    """
    output_root = luigi.Parameter()
    delete_output_root = luigi.BooleanParameter(default=False)

    def output(self):
        return get_target_from_url(url_path_join(self.output_root, MARKER_FILENAME))

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

    def multi_output_reducer(self, _key, _values, _output_file):
        """Returns an iterable of strings that are written out to the appropriate output file for this key."""
        return iter(tuple())

    def output_path_for_key(self, _key):
        """
        Returns a URL that is unique to the given key.

        All values returned from the reducer for the given key will be output to the file specified by the URL returned
        from this function.
        """
        return None

    def __init__(self, *args, **kwargs):
        super(MultiOutputMapReduceJobTask, self).__init__(*args, **kwargs)
        if self.delete_output_root:
            # If requested, make sure that the output directory is empty.  This gets rid
            # of any generated data files from a previous run (that might not get
            # regenerated in this run).  It also makes sure that the marker file
            # (i.e. the output target) will be removed, so that external functionality
            # will know that the generation of data files is not complete.
            output_dir_target = get_target_from_url(self.output_root)
            if output_dir_target.exists():
                output_dir_target.remove()
