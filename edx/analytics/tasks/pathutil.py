"""
Helper classes to specify file dependencies for input and output.

Supports inputs from S3 and local FS.
Supports outputs to HDFS, S3, and local FS.

"""

import boto
import glob

import luigi
import luigi.s3
import luigi.hdfs
import luigi.format

from edx.analytics.tasks.s3_util import generate_s3_sources
from edx.analytics.tasks.url import ExternalURL, url_path_join, get_target_from_url


class PathSetTask(luigi.Task):
    """
    A task to select a subset of files in an S3 bucket or local FS.

    Parameters:

      src: a URL pointing to a folder in s3:// or local FS.
      include:  a list of patterns to use to select.  Multiple patterns are OR'd.
      manifest: a URL pointing to a manifest file location.
    """
    src = luigi.Parameter()
    include = luigi.Parameter(is_list=True, default=('*',))
    manifest = luigi.Parameter(default=None)

    def __init__(self, *args, **kwargs):
        super(PathSetTask, self).__init__(*args, **kwargs)
        self.s3_conn = None

    def generate_file_list(self):
        """Yield each individual path given a source folder and a set of glob expressions."""
        if self.src.startswith('s3'):
            # connect lazily as needed:
            if self.s3_conn is None:
                self.s3_conn = boto.connect_s3()
            for _bucket, root, path in generate_s3_sources(self.s3_conn, self.src, self.include):
                source = url_path_join(self.src, root, path)
                yield ExternalURL(source)
        else:
            filelist = []
            for include_val in self.include:
                glob_pattern = "{src}/{include}".format(src=self.src, include=include_val)
                filelist.extend(glob.glob(glob_pattern))
            for filepath in filelist:
                yield ExternalURL(filepath)

    def manifest_file_list(self):
        """Write each individual path to a manifest file and yield the path to that file."""
        manifest_target = get_target_from_url(self.manifest)
        if not manifest_target.exists():
            with manifest_target.open('w') as manifest_file:
                for external_url_task in self.generate_file_list():
                    manifest_file.write(external_url_task.url + '\n')

        yield ExternalURL(self.manifest)

    def requires(self):
        if self.manifest is not None:
            return self.manifest_file_list()
        else:
            return self.generate_file_list()


    def complete(self):
        # An optimization: just declare that the task is always
        # complete, by definition, because it is whatever files were
        # requested that match the filter, not a set of files whose
        # existence needs to be checked or generated again.
        return True

    def output(self):
        return [task.output() for task in self.requires()]
