import abc


class BaseError(Exception):
    """
    Base error.
    """

    __metaclass__ = abc.ABCMeta

    message = None

    def __str__(self):
        return self.message


class LearnerNotFoundError(BaseError):
    """
    Raise learner not found for a course.
    """
    def __init__(self, *args, **kwargs):
        course_id = kwargs.pop('course_id')
        username = kwargs.pop('username')
        super(LearnerNotFoundError, self).__init__(*args, **kwargs)
        self.message = self.message_template.format(username=username, course_id=course_id)

    @property
    def message_template(self):
        return 'Learner {username} not found for course {course_id}.'


class LearnerEngagementTimelineNotFoundError(BaseError):
    """
    Raise learner engagement timeline not found for a course.
    """
    def __init__(self, *args, **kwargs):
        course_id = kwargs.pop('course_id')
        username = kwargs.pop('username')
        super(LearnerEngagementTimelineNotFoundError, self).__init__(*args, **kwargs)
        self.message = self.message_template.format(username=username, course_id=course_id)

    @property
    def message_template(self):
        return 'Learner {username} engagement timeline not found for course {course_id}.'


class CourseNotSpecifiedError(BaseError):
    """
    Raise if course not specified.
    """
    def __init__(self, *args, **kwargs):
        super(CourseNotSpecifiedError, self).__init__(*args, **kwargs)
        self.message = 'Course id/key not specified.'


class CourseKeyMalformedError(BaseError):
    """
    Raise if course id/key malformed.
    """
    def __init__(self, *args, **kwargs):
        course_id = kwargs.pop('course_id')
        super(CourseKeyMalformedError, self).__init__(*args, **kwargs)
        self.message = self.message_template.format(course_id=course_id)

    @property
    def message_template(self):
        return 'Course id/key {course_id} malformed.'


class ParameterValueError(BaseError):
    """Raise if multiple incompatible parameters were provided."""
    def __init__(self, message, *args, **kwargs):
        super(ParameterValueError, self).__init__(*args, **kwargs)
        self.message = message


class ReportFileNotFoundError(BaseError):
    """
    Raise if we couldn't find the file we need to produce the report
    """
    def __init__(self, *args, **kwargs):
        course_id = kwargs.pop('course_id')
        report_name = kwargs.pop('report_name')
        super(ReportFileNotFoundError, self).__init__(*args, **kwargs)
        self.message = self.message_template.format(course_id=course_id, report_name=report_name)

    @property
    def message_template(self):
        return 'Could not find report \'{report_name}\' for course {course_id}.'


class CannotCreateReportDownloadLinkError(BaseError):
    """
    Raise if we cannot create a link for the file to be downloaded
    """

    message = 'Could not create a downloadable link to the report.'
