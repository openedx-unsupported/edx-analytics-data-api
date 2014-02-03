"""
Utility methods for interacting with S3 via boto.
"""

from fnmatch import fnmatch
from urlparse import urlparse


def get_s3_bucket_key_names(url):
    """Extract the bucket and key names from a S3 URL"""
    parts = urlparse(url)
    return (parts.netloc.strip('/'), parts.path.strip('/'))


def join_as_s3_url(bucket, root, path):
    """Combine bucket name, root path and relative path into a S3 URL"""
    return 's3://{0}/{1}/{2}'.format(bucket, root, path)


def get_s3_key(s3_conn, url):
    """Returns an S3 key for use in further boto actions."""
    bucket_name, key_name = get_s3_bucket_key_names(url)
    bucket = s3_conn.get_bucket(bucket_name)
    key = bucket.get_key(key_name)
    return key


def generate_s3_sources(s3_conn, source, patterns):
    """
    Returns a list of S3 sources that match filters.

    Args:

      s3_conn: a boto connection to S3.
      source:  a url to S3.
      patterns:  a list of strings, each of which defines a pattern to match.

    Yields:

      (bucket, root, path) tuples for each matching file on S3.

      where `bucket` and `root` are derived from the source url,
      and `path` is a matching path relative to the `source`.

    Does not include zero-length files.
    """
    bucket_name, root = get_s3_bucket_key_names(source)

    bucket = s3_conn.get_bucket(bucket_name)

    # Skip keys that have zero size.  This allows directories
    # to be skipped, but also skips legitimate files that are
    # also zero-length.
    keys = (s.key for s in bucket.list(root) if s.size > 0)

    # Make paths relative by removing root
    paths = (k[len(root):].lstrip('/') for k in keys)

    # Filter only paths that match the include patterns
    paths = _filter_matches(patterns, paths)

    return ((bucket.name, root, path) for path in paths)


def _filter_matches(patterns, names):
    """Return only key names that match any of the include patterns."""
    func = lambda n: any(fnmatch(n, p) for p in patterns)
    return (n for n in names if func(n))
