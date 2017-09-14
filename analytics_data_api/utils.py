import datetime
from importlib import import_module
import re

from django.db.models import Q
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.exceptions import SuspiciousFileOperation, SuspiciousOperation
from rest_framework.authtoken.models import Token
from opaque_keys.edx.locator import CourseKey
from opaque_keys import InvalidKeyError

from analytics_data_api.v0.exceptions import (
    ReportFileNotFoundError,
    CannotCreateReportDownloadLinkError
)


def get_filename_safe_course_id(course_id, replacement_char='_'):
    """
    Create a representation of a course_id that can be used safely in a filepath.
    """
    try:
        course_key = CourseKey.from_string(course_id)
        filename = unicode(replacement_char).join([course_key.org, course_key.course, course_key.run])
    except InvalidKeyError:
        # If the course_id doesn't parse, we will still return a value here.
        filename = course_id

    # The safest characters are A-Z, a-z, 0-9, <underscore>, <period> and <hyphen>.
    # We represent the first four with \w.
    # TODO: Once we support courses with unicode characters, we will need to revisit this.
    return re.sub(r'[^\w\.\-]', unicode(replacement_char), filename)


def delete_user_auth_token(username):
    """
    Deletes the authentication tokens for the user with the given username

    If no user exists, NO error is returned.
    :param username: Username of the user whose authentication tokens should be deleted
    :return: None
    """
    Token.objects.filter(user__username=username).delete()


def set_user_auth_token(user, key):
    """
    Sets the authentication for the given User.

    Raises an AttributeError if *different* User with the specified key already exists.

    :param user: User whose authentication is being set
    :param key: New authentication key
    :return: None
    """
    # Check that no other user has the same key
    if Token.objects.filter(~Q(user=user), key=key).exists():
        raise AttributeError("The key %s is already in use by another user.", key)

    Token.objects.filter(user=user).delete()
    Token.objects.create(user=user, key=key)

    print "Set API key for user %s to %s" % (user, key)


def matching_tuple(answer):
    """ Return tuple containing values which must match for consolidation. """
    return (
        answer.question_text,
        answer.answer_value,
        answer.problem_display_name,
        answer.correct,
    )


def dictfetchall(cursor):
    """Returns all rows from a cursor as a dict"""

    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]


def load_fully_qualified_definition(definition):
    """ Returns the class given the full definition. """
    module_name, class_name = definition.rsplit('.', 1)
    module = import_module(module_name)
    return getattr(module, class_name)


def date_range(start_date, end_date, delta=datetime.timedelta(days=1)):
    """
    Returns a generator that iterates over the date range [start_date, end_date)
    (start_date inclusive, end_date exclusive).  Each date in the range is
    offset from the previous date by a change of `delta`, which defaults
    to one day.

    Arguments:
        start_date (datetime.datetime): The start date of the range, inclusive
        end_date (datetime.datetime): The end date of the range, exclusive
        delta (datetime.timedelta): The change in time between dates in the
            range.

    Returns:
        Generator: A generator which iterates over all dates in the specified
        range.
    """
    cur_date = start_date
    while cur_date < end_date:
        yield cur_date
        cur_date += delta


def get_course_report_download_details(course_id, report_name):
    """
    Determine the path that the report file should be located at,
    then return metadata sufficient for downloading it.
    """
    report_location_template = getattr(
        settings,
        'COURSE_REPORT_FILE_LOCATION_TEMPLATE',
        '{course_id}_{report_name}.csv'
    )
    # Course IDs contain characters that may not be valid in various
    # filesystems; here we remove them before looking for the file or
    # creating the downloadable filename.
    course_id = get_filename_safe_course_id(course_id)
    report_location = report_location_template.format(
        course_id=course_id,
        report_name=report_name
    )
    try:
        if not default_storage.exists(report_location):
            raise ReportFileNotFoundError(course_id=course_id, report_name=report_name)
    except (
            AttributeError,
            NotImplementedError,
            ImportError,
            SuspiciousFileOperation,
            SuspiciousOperation
    ):
        # Error out if:
        # - We don't have a method to determine file existence
        # - Such a method isn't implemented
        # - We can't import the specified storage class
        # - We don't have privileges for the specified file location
        raise CannotCreateReportDownloadLinkError

    try:
        last_modified = default_storage.modified_time(report_location)
    except (NotImplementedError, AttributeError):
        last_modified = None

    try:
        download_size = default_storage.size(report_location)
    except (NotImplementedError, AttributeError):
        download_size = None

    download_filename = '{}-{}-{}.csv'.format(
        course_id,
        report_name,
        # We need a date for the filename; if we don't know when it was last modified,
        # use the current date and time to stamp the filename.
        (last_modified or datetime.datetime.utcnow()).strftime('%Y%m%dT%H%M%SZ')
    )
    url, expiration_date = get_file_object_url(report_location, download_filename)

    details = {
        'course_id': course_id,
        'report_name': report_name,
        'download_url': url
    }
    # These are all optional items that aren't guaranteed. The URL isn't guaranteed
    # either, but we'll raise an exception earlier if we don't have it.
    if last_modified is not None:
        details.update({'last_modified': last_modified.strftime(settings.DATETIME_FORMAT)})
    if expiration_date is not None:
        details.update({'expiration_date': expiration_date.strftime(settings.DATETIME_FORMAT)})
    if download_size is not None:
        details.update({'file_size': download_size})
    return details


def get_file_object_url(filename, download_filename):
    """
    Retrieve a download URL for the file, as well as a datetime object
    indicating when the URL expires.

    We need to pass extra details to the URL method, above and beyond just the
    file location, to give us what we need.

    This method supports S3 storage's optional response parameters that allow
    us to set expiry time, as well as content disposition and content type
    on any download made using the generated link.
    """
    # Default to expiring the link after two minutes
    expire_length = getattr(settings, 'COURSE_REPORT_DOWNLOAD_EXPIRY_TIME', 120)
    expires_at = get_expiration_date(expire_length)
    try:
        url = default_storage.url(
            name=filename,
            response_headers={
                'response-content-disposition': 'attachment; filename={}'.format(download_filename),
                'response-content-type': 'text/csv',
                # The Expires header requires a very particular timestamp format
                'response-expires': expires_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
            },
            expire=expire_length
        )
    except TypeError:
        # We got a TypeError when calling `.url()`; typically, this means that the arguments
        # we passed aren't allowed. Retry with no extra arguments.
        try:
            url = default_storage.url(name=filename)
            expires_at = None
        except (AttributeError, TypeError, NotImplementedError):
            # Another error, for unknown reasons. Can't recover from this; fail fast
            raise CannotCreateReportDownloadLinkError
    except (AttributeError, NotImplementedError):
        # Either we can't find a .url() method, or we can't use it. Raise an exception.
        raise CannotCreateReportDownloadLinkError
    return url, expires_at


def get_expiration_date(seconds):
    """
    Determine when a given link will expire, based on a given lifetime
    """
    return datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)
