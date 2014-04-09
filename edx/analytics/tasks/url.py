"""
Support URLs.  Specifically, we want to be able to refer to data stored in a
variety of locations and formats using a standard URL syntax.

Examples::

    s3://some-bucket/path/to/file
    /path/to/local/file.gz
    hdfs://some/directory/
"""
from __future__ import absolute_import

import os
import urlparse

import luigi
import luigi.format
import luigi.hdfs
import luigi.s3

from edx.analytics.tasks.s3_util import ScalableS3Client, S3HdfsTarget


class ExternalURL(luigi.ExternalTask):
    """Simple Task that returns a target based on its URL"""
    url = luigi.Parameter()

    def output(self):
        return get_target_from_url(self.url)


class IgnoredTarget(luigi.hdfs.HdfsTarget):
    """Dummy target for use in Hadoop jobs that produce no explicit output file."""
    def __init__(self):
        super(IgnoredTarget, self).__init__(is_tmp=True)

    def exists(self):
        return False

    def open(self, mode='r'):
        return open('/dev/null', mode)


DEFAULT_TARGET_CLASS = luigi.LocalTarget
URL_SCHEME_TO_TARGET_CLASS = {
    'hdfs': luigi.hdfs.HdfsTarget,
    's3': S3HdfsTarget,
    's3n': S3HdfsTarget,
    'file': luigi.LocalTarget,
    's3+https': luigi.s3.S3Target,
}


def get_target_from_url(url):
    """Returns a luigi target based on the url scheme"""
    parsed_url = urlparse.urlparse(url)
    target_class = URL_SCHEME_TO_TARGET_CLASS.get(parsed_url.scheme, DEFAULT_TARGET_CLASS)
    kwargs = {}
    if issubclass(target_class, luigi.hdfs.HdfsTarget) and url.endswith('/'):
        kwargs['format'] = luigi.hdfs.PlainDir
    if issubclass(target_class, luigi.LocalTarget):
        url = parsed_url.path
        if url.endswith('.gz'):
            kwargs['format'] = luigi.format.Gzip
    if issubclass(target_class, luigi.s3.S3Target):
        kwargs['client'] = ScalableS3Client()

    url = url.rstrip('/')
    return target_class(url, **kwargs)


def url_path_join(url, *extra_path):
    """
    Extend the path component of the given URL.  Relative paths extend the
    existing path, absolute paths replace it.  Special path elements like '.'
    and '..' are not treated any differently than any other path element.

    Examples:

        url=http://foo.com/bar, extra_path=baz -> http://foo.com/bar/baz
        url=http://foo.com/bar, extra_path=/baz -> http://foo.com/baz
        url=http://foo.com/bar, extra_path=../baz -> http://foo.com/bar/../baz

    Args:

        url (str): The URL to modify.
        extra_path (str): The path to join with the current URL path.

    Returns:
        The URL with the path component joined with `extra_path` argument.
    """
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)
    joined_path = os.path.join(path, *extra_path)
    return urlparse.urlunparse((scheme, netloc, joined_path, params, query, fragment))
