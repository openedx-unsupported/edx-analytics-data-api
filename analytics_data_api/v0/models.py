from django.db import models
from analytics_data_api.v0.managers import CourseManager


class Course(models.Model):
    course_id = models.CharField(unique=True, max_length=255)

    objects = CourseManager()   # pylint: disable=no-value-for-parameter

    class Meta(object):
        db_table = 'courses'


class CourseActivityByWeek(models.Model):
    """A count of unique users who performed a particular action during a week."""

    class Meta(object):
        db_table = 'course_activity'

    course = models.ForeignKey(Course, null=False)
    interval_start = models.DateTimeField()
    interval_end = models.DateTimeField()
    activity_type = models.CharField(db_index=True, max_length=255)
    count = models.IntegerField()

    @classmethod
    def get_most_recent(cls, course_id, activity_type):
        """Activity for the week that was mostly recently computed."""
        return cls.objects.filter(course__course_id=course_id, activity_type=activity_type).latest('interval_end')


class BaseCourseEnrollment(models.Model):
    course = models.ForeignKey(Course, null=False)
    interval_start = models.DateTimeField(null=False)
    interval_end = models.DateTimeField(null=False)
    num_enrolled_students = models.IntegerField(null=False)

    class Meta(object):
        abstract = True


class CourseEnrollmentByBirthYear(BaseCourseEnrollment):
    birth_year = models.IntegerField(null=False)

    class Meta(object):
        db_table = 'course_enrollment_birth_year'
        ordering = ('course', 'birth_year')


class EducationLevel(models.Model):
    name = models.CharField(max_length=255, null=False, unique=True)
    short_name = models.CharField(max_length=255, null=False, unique=True)

    class Meta(object):
        db_table = 'education_levels'


class CourseEnrollmentByEducation(BaseCourseEnrollment):
    education_level = models.ForeignKey(EducationLevel)

    class Meta(object):
        db_table = 'course_enrollment_education_level'
        ordering = ('course', 'education_level')


class CourseEnrollmentByGender(BaseCourseEnrollment):
    gender = models.CharField(max_length=255, null=False)

    class Meta(object):
        db_table = 'course_enrollment_gender'
        ordering = ('course', 'gender')
