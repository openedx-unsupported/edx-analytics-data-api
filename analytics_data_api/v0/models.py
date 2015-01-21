from django.db import models

from analytics_data_api.constants import country, genders


class CourseActivityWeekly(models.Model):
    """A count of unique users who performed a particular action during a week."""

    class Meta(object):
        db_table = 'course_activity'
        index_together = [['course_id', 'activity_type']]
        ordering = ('interval_end', 'interval_start', 'course_id')
        get_latest_by = 'interval_end'

    course_id = models.CharField(db_index=True, max_length=255)
    interval_start = models.DateTimeField()
    interval_end = models.DateTimeField(db_index=True)
    activity_type = models.CharField(db_index=True, max_length=255, db_column='label')
    count = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)

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


class CourseEnrollmentModeDaily(BaseCourseEnrollment):
    mode = models.CharField(max_length=255)

    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_mode_daily'
        ordering = ('date', 'course_id', 'mode')
        unique_together = [('course_id', 'date', 'mode')]


class CourseEnrollmentByBirthYear(BaseCourseEnrollment):
    birth_year = models.IntegerField(null=False)

    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_birth_year_daily'
        ordering = ('date', 'course_id', 'birth_year')
        unique_together = [('course_id', 'date', 'birth_year')]


class CourseEnrollmentByEducation(BaseCourseEnrollment):
    education_level = models.CharField(max_length=255, null=True)

    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_education_level_daily'
        ordering = ('date', 'course_id', 'education_level')
        unique_together = [('course_id', 'date', 'education_level')]


class CourseEnrollmentByGender(BaseCourseEnrollment):
    CLEANED_GENDERS = {
        u'f': genders.FEMALE,
        u'm': genders.MALE,
        u'o': genders.OTHER
    }

    gender = models.CharField(max_length=255, null=True, db_column='gender')

    @property
    def cleaned_gender(self):
        """
        Returns the gender with full names and 'unknown' replacing null/None.
        """
        return self.CLEANED_GENDERS.get(self.gender, genders.UNKNOWN)

    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_gender_daily'
        ordering = ('date', 'course_id', 'gender')
        unique_together = [('course_id', 'date', 'gender')]


class ProblemResponseAnswerDistribution(models.Model):
    """ Each row stores the count of a particular answer to a response in a problem in a course (usage). """

    class Meta(object):
        db_table = 'answer_distribution'

    course_id = models.CharField(db_index=True, max_length=255)
    module_id = models.CharField(db_index=True, max_length=255)
    part_id = models.CharField(db_index=True, max_length=255)
    correct = models.NullBooleanField()
    count = models.IntegerField()
    value_id = models.CharField(db_index=True, max_length=255, null=True)
    answer_value = models.TextField(null=True, db_column='answer_value_text')
    variant = models.IntegerField(null=True)
    problem_display_name = models.TextField(null=True)
    question_text = models.TextField(null=True)
    created = models.DateTimeField(auto_now_add=True)


class CourseEnrollmentByCountry(BaseCourseEnrollment):
    country_code = models.CharField(max_length=255, null=False, db_column='country_code')

    @property
    def country(self):
        """
        Returns a Country object representing the country in this model's country_code.
        """
        return country.get_country(self.country_code)

    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_location_current'
        ordering = ('date', 'course_id', 'country_code')
        unique_together = [('course_id', 'date', 'country_code')]


class GradeDistribution(models.Model):
    """ Each row stores the count of a particular grade on a module for a given course. """

    class Meta(object):
        db_table = 'grade_distribution'

    module_id = models.CharField(db_index=True, max_length=255)
    course_id = models.CharField(db_index=True, max_length=255)
    grade = models.IntegerField()
    max_grade = models.IntegerField()
    count = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)


class SequentialOpenDistribution(models.Model):
    """ Each row stores the count of views a particular module has had in a given course. """

    class Meta(object):
        db_table = 'sequential_open_distribution'

    module_id = models.CharField(db_index=True, max_length=255)
    course_id = models.CharField(db_index=True, max_length=255)
    count = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)
