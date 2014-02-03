import os.path

import boto
import luigi
import luigi.s3

from edx.analytics.tasks.s3_util import join_as_s3_url, get_s3_bucket_key_names, generate_s3_sources, get_s3_key


class S3Copy(luigi.Task):
    """
    Copy a file from one S3 location to another.

    Files in the destination are overriden unless they have the same.
    The copy is done using boto.

    Parameters:

    `source`: location of original s3 file
    `destination`: location where to copy the file

    """
    source = luigi.Parameter()
    destination = luigi.Parameter()

    def __init__(self, *args, **kwargs):
        super(S3Copy, self).__init__(*args, **kwargs)
        self.s3 = boto.connect_s3()

    def extra_modules(self):
        return [boto]

    def requires(self):
        return luigi.s3.S3PathTask(self.source)

    def output(self):
        return luigi.s3.S3Target(self.destination)

    def complete(self):
        # Check if the destination file has been copied already by
        # verifying its existence, and if so, determining if it has
        # the same content as the source by using md5 hashes.

        src = self.input()
        dst = self.output()

        if not dst.exists():
            return False

        src_key = get_s3_key(self.s3, src.path)
        dst_key = get_s3_key(self.s3, dst.path)

        if dst_key.size != src_key.size:
            return False

        # Check the md5 hashes of the keys.
        if dst_key.etag != src_key.etag:
            return False

        return True

    def run(self):
        src_url = self.input().path
        dst_url = self.output().path

        src_key = get_s3_key(self.s3, src_url)
        dst_bucket_name, dst_key_name = get_s3_bucket_key_names(dst_url)

        # The copy overwrites the destination. The task checks if
        # that is necessary during the `complete()` call.
        src_key.copy(dst_bucket_name, dst_key_name)


class S3Sync(luigi.Task):
    """
    Synchronizes a s3 root path with another.

    The destination file paths are relative to the source and destination
    roots. For example if:

    source: s3://source-bucket/foo/bar
    destination: s3://destination-bucket/baz
    include = ['*.gz']

    The file s3://source-bucket/foo/bar/zoo/lion.gz will be copied to
    s3://destination-bucket/baz/zoo/lion.gz

    Parameters:

    `source`: root S3 path where of the keys to be copied
    `destination`: root S3 path where the keys will be copied
    `include`: list of glob expressions of the keys to include.
               default is ['*']

    """

    source = luigi.Parameter()
    destination = luigi.Parameter()
    include = luigi.Parameter(is_list=True, default=('*',))

    def __init__(self, *args, **kwargs):
        super(S3Sync, self).__init__(*args, **kwargs)
        self.s3 = boto.connect_s3()

    def extra_modules(self):
        return [boto]

    def requires(self):
        for bucket, root, path in generate_s3_sources(self.s3, self.source, self.include):
            source = join_as_s3_url(bucket, root, path)
            destination = os.path.join(self.destination, path)
            yield S3Copy(source, destination)

    def output(self):
        for task in self.requires():
            yield task.output()
