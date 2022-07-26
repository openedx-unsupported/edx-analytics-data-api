import abc


class BaseError(Exception, metaclass=abc.ABCMeta):
    """
    Base error.
    """

    message = None

    def __str__(self):
        return self.message


class CourseNotSpecifiedError(BaseError):
    """
    Raise if course not specified.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = 'Course id/key not specified.'


class CourseKeyMalformedError(BaseError):
    """
    Raise if course id/key malformed.
    """
    def __init__(self, *args, **kwargs):
        course_id = kwargs.pop('course_id')
        super().__init__(*args, **kwargs)
        self.message = self.message_template.format(course_id=course_id)

    @property
    def message_template(self):
        return 'Course id/key {course_id} malformed.'


class ReportFileNotFoundError(BaseError):
    """
    Raise if we couldn't find the file we need to produce the report
    """
    def __init__(self, *args, **kwargs):
        course_id = kwargs.pop('course_id')
        report_name = kwargs.pop('report_name')
        super().__init__(*args, **kwargs)
        self.message = self.message_template.format(course_id=course_id, report_name=report_name)

    @property
    def message_template(self):
        return 'Could not find report \'{report_name}\' for course {course_id}.'


class CannotCreateReportDownloadLinkError(BaseError):
    """
    Raise if we cannot create a link for the file to be downloaded
    """

    message = 'Could not create a downloadable link to the report.'
