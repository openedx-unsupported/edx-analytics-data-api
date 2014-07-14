from django.db import models
from analytics_data_api.v0.managers import CourseManager


class Course(models.Model):
    course_id = models.CharField(unique=True, max_length=255)

    objects = CourseManager()  # pylint: disable=no-value-for-parameter

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
    date = models.DateField(null=False)
    count = models.IntegerField(null=False)

    class Meta(object):
        abstract = True
        unique_together = [('course', 'date',)]


class CourseEnrollmentDaily(BaseCourseEnrollment):
    class Meta(object):
        db_table = 'course_enrollment_daily'
        ordering = ('course', '-date')
        unique_together = [('course', 'date',)]
        get_latest_by = 'date'


class CourseEnrollmentByBirthYear(BaseCourseEnrollment):
    birth_year = models.IntegerField(null=False)

    class Meta(object):
        db_table = 'course_enrollment_birth_year'
        ordering = ('course', 'birth_year')
        unique_together = [('course', 'date', 'birth_year')]


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
        unique_together = [('course', 'date', 'education_level')]


class CourseEnrollmentByGender(BaseCourseEnrollment):
    gender = models.CharField(max_length=255, null=False)

    class Meta(object):
        db_table = 'course_enrollment_gender'
        ordering = ('course', 'gender')
        unique_together = [('course', 'date', 'gender')]


class ProblemResponseAnswerDistribution(models.Model):
    """ Each row stores the count of a particular answer to a response in a problem in a course (usage). """

    class Meta(object):
        db_table = 'answer_distribution'

    course_id = models.CharField(db_index=True, max_length=255, db_column='course_id')
    module_id = models.CharField(db_index=True, max_length=255, db_column='module_id')
    part_id = models.CharField(db_index=True, max_length=255, db_column='part_id')
    correct = models.BooleanField(db_column='correct')
    count = models.IntegerField(db_column='count')
    value_id = models.CharField(db_index=True, max_length=255, db_column='value_id', null=True)
    answer_value_text = models.TextField(db_column='answer_value_text', null=True)
    answer_value_numeric = models.FloatField(db_column='answer_value_numeric', null=True)
    variant = models.IntegerField(db_column='variant', null=True)
    created = models.DateTimeField(auto_now_add=True, db_column='created')
