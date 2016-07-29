from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

from analytics_data_api.v0.exceptions import (CourseNotSpecifiedError, CourseKeyMalformedError)


class CourseViewMixin(object):
    """
    Captures the course_id from the url and validates it.
    """

    course_id = None

    def get(self, request, *args, **kwargs):
        self.course_id = self.kwargs.get('course_id', request.query_params.get('course_id', None))

        if not self.course_id:
            raise CourseNotSpecifiedError()
        try:
            CourseKey.from_string(self.course_id)
        except InvalidKeyError:
            raise CourseKeyMalformedError(course_id=self.course_id)
        return super(CourseViewMixin, self).get(request, *args, **kwargs)
