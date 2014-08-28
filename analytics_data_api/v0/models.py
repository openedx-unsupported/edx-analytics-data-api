from django.db import models
from iso3166 import countries


class CourseActivityByWeek(models.Model):
    """A count of unique users who performed a particular action during a week."""

    class Meta(object):
        db_table = 'course_activity'
        index_together = [['course_id', 'activity_type']]

    course_id = models.CharField(db_index=True, max_length=255)
    interval_start = models.DateTimeField()
    interval_end = models.DateTimeField()
    activity_type = models.CharField(db_index=True, max_length=255, db_column='label')
    count = models.IntegerField()

    @classmethod
    def get_most_recent(cls, course_id, activity_type):
        """Activity for the week that was mostly recently computed."""
        return cls.objects.filter(course_id=course_id, activity_type=activity_type).latest('interval_end')


class BaseCourseEnrollment(models.Model):
    course_id = models.CharField(max_length=255)
    date = models.DateField(null=False, db_index=True)
    count = models.IntegerField(null=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta(object):
        abstract = True
        get_latest_by = 'date'
        index_together = [('course_id', 'date',)]


class CourseEnrollmentDaily(BaseCourseEnrollment):
    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_daily'
        ordering = ('date', 'course_id')
        unique_together = [('course_id', 'date',)]


class CourseEnrollmentByBirthYear(BaseCourseEnrollment):
    birth_year = models.IntegerField(null=False)

    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_birth_year_daily'
        ordering = ('date', 'course_id', 'birth_year')
        unique_together = [('course_id', 'date', 'birth_year')]


class EducationLevel(models.Model):
    name = models.CharField(max_length=255, null=False, unique=True)
    short_name = models.CharField(max_length=255, null=False, unique=True)

    class Meta(object):
        db_table = 'education_levels'

    def __unicode__(self):
        return "{0} - {1}".format(self.short_name, self.name)


class CourseEnrollmentByEducation(BaseCourseEnrollment):
    education_level = models.ForeignKey(EducationLevel)

    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_education_level_daily'
        ordering = ('date', 'course_id', 'education_level')
        unique_together = [('course_id', 'date', 'education_level')]


class CourseEnrollmentByGender(BaseCourseEnrollment):
    gender = models.CharField(max_length=255, null=False)

    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_gender_daily'
        ordering = ('date', 'course_id', 'gender')
        unique_together = [('course_id', 'date', 'gender')]


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


class CourseEnrollmentByCountry(BaseCourseEnrollment):
    country_code = models.CharField(max_length=255, null=False, db_column='country_code')

    @property
    def country(self):
        """
        Returns a Country object representing the country in this model's country_code.
        """
        try:
            return countries.get(self.country_code)
        except (KeyError, ValueError):
            # Country code is not valid ISO-3166
            return None

    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_location_current'
        ordering = ('date', 'course_id', 'country_code')
        unique_together = [('course_id', 'date', 'country_code')]
