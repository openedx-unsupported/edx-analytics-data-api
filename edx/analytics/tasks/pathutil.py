"""
Helper classes to specify file dependencies for input and output.

Supports inputs from S3 and local FS.
Supports outputs to HDFS, S3, and local FS.

"""

import os
import boto
import glob

import luigi
import luigi.s3
import luigi.hdfs
import luigi.format

from edx.analytics.tasks.s3_util import join_as_s3_url, generate_s3_sources


class LocalPathTask(luigi.ExternalTask):
    """
    An external task that to require existence of
    a path in a local file system.

    Treats files ending with .gz as Gzip files.
    """
    path = luigi.Parameter()

    def output(self):
        if self.path.endswith('.gz'):
            yield luigi.LocalTarget(self.path, format=luigi.format.Gzip)
        else:
            yield luigi.LocalTarget(self.path)


class HdfsPathTask(luigi.ExternalTask):
    """
    An external task that to require existence of
    a path in HDFS.
    """
    path = luigi.Parameter()

    def output(self):
        return luigi.hdfs.HdfsTarget(self.path)


class PathSetTask(luigi.Task):
    """
    A task to select a subset of files in an S3 bucket or local FS.

    Parameters:

      src: a URL pointing to a folder in s3:// or local FS.
      include:  a list of patterns to use to select.  Multiple patterns are OR'd.
      run_locally:  if True, use S3PathTask instead of HDFSPathTask, to permit
          reading S3 data when running in local mode.
    """
    src = luigi.Parameter()
    include = luigi.Parameter(is_list=True, default=('*',))
    # TODO: modify this to get default values from a configuration file,
    # and use that to determine whether running in a cluster or locally.
    # It will be decoupled from the use of S3PathTask/HDFSPathTask.
    # Instead, these will be distinguished by different protocol names.
    run_locally = luigi.BooleanParameter()

    def __init__(self, *args, **kwargs):
        super(PathSetTask, self).__init__(*args, **kwargs)
        self.s3_conn = None

    def requires(self):
        if self.src.startswith('s3'):
            # connect lazily as needed:
            if self.s3_conn is None:
                self.s3_conn = boto.connect_s3()
            for bucket, root, path in generate_s3_sources(self.s3_conn, self.src, self.include):
                source = join_as_s3_url(bucket, root, path)
                if self.run_locally:
                    yield luigi.s3.S3PathTask(source)
                else:
                    yield HdfsPathTask(source)
        else:
            filelist = []
            for include_val in self.include:
                glob_pattern = "{src}/{include}".format(src=self.src, include=include_val)
                filelist.extend(glob.glob(glob_pattern))
            for filepath in filelist:
                yield LocalPathTask(filepath)

    def complete(self):
        # An optimization: just declare that the task is always
        # complete, by definition, because it is whatever files were
        # requested that match the filter, not a set of files whose
        # existence needs to be checked or generated again.
        return True

    def output(self):
        return [task.output() for task in self.requires()]


def get_target_for_url(dest, output_name, run_locally=False):
    """
    Generate an appropriate target for a given path, depending on protocol.

    Parameters:

      dest: a URL pointing to a folder in s3:// or hdfs:// or local FS.
      output_name:  name of file to be output.
      run_locally:  if True, use S3Target instead of HdfsTarget, to permit
          writing S3 data when running in local mode.

    """
    output_url = os.path.join(dest, output_name)
    if output_url.startswith('s3://'):
        if run_locally:
            return luigi.s3.S3Target(output_url)
        else:
            return luigi.hdfs.HdfsTarget(output_url)
    elif output_url.startswith('hdfs://'):
        return luigi.hdfs.HdfsTarget(output_url)
    else:
        return luigi.LocalTarget(output_url)
