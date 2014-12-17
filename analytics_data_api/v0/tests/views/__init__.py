from opaque_keys.edx.keys import CourseKey

DEMO_COURSE_ID = u'course-v1:edX+DemoX+Demo_2014'


class DemoCourseMixin(object):
    course_key = None
    course_id = None

    @classmethod
    def setUpClass(cls):
        cls.course_id = DEMO_COURSE_ID
        cls.course_key = CourseKey.from_string(cls.course_id)
        super(DemoCourseMixin, cls).setUpClass()
