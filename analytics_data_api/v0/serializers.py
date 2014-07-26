from django.conf import settings
from rest_framework import serializers
from analytics_data_api.v0 import models


class CourseIdMixin(object):
    def get_course_id(self, obj):
        return obj.course.course_id


class RequiredSerializerMethodField(serializers.SerializerMethodField):
    required = True


class CourseActivityByWeekSerializer(serializers.ModelSerializer, CourseIdMixin):
    """
    Representation of CourseActivityByWeek that excludes the id field.

    This table is managed by the data pipeline, and records can be removed and added at any time. The id for a
    particular record is likely to change unexpectedly so we avoid exposing it.
    """

    course_id = RequiredSerializerMethodField('get_course_id')

    class Meta(object):
        model = models.CourseActivityByWeek
        fields = ('interval_start', 'interval_end', 'activity_type', 'count', 'course_id')


class ProblemResponseAnswerDistributionSerializer(serializers.ModelSerializer):
    """
    Representation of the Answer Distribution table, without id.

    This table is managed by the data pipeline, and records can be removed and added at any time. The id for a
    particular record is likely to change unexpectedly so we avoid exposing it.
    """

    class Meta(object):
        model = models.ProblemResponseAnswerDistribution
        fields = (
            'course_id',
            'module_id',
            'part_id',
            'correct',
            'count',
            'value_id',
            'answer_value_text',
            'answer_value_numeric',
            'variant',
            'created'
        )


class BaseCourseEnrollmentModelSerializer(serializers.ModelSerializer, CourseIdMixin):
    course_id = RequiredSerializerMethodField('get_course_id')
    date = serializers.DateField(format=settings.DATE_FORMAT)


class CourseEnrollmentDailySerializer(BaseCourseEnrollmentModelSerializer):
    """ Representation of course enrollment for a single day and course. """

    class Meta(object):
        model = models.CourseEnrollmentDaily
        fields = ('course_id', 'date', 'count')


class CountrySerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()


# pylint: disable=no-value-for-parameter
class EducationLevelSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = models.EducationLevel
        fields = ('name', 'short_name')


class CourseEnrollmentByCountrySerializer(BaseCourseEnrollmentModelSerializer):
    # pylint: disable=unexpected-keyword-arg
    country = CountrySerializer(many=False)

    class Meta(object):
        model = models.CourseEnrollmentByCountry
        fields = ('date', 'course_id', 'country', 'count')


class CourseEnrollmentByGenderSerializer(BaseCourseEnrollmentModelSerializer):
    class Meta(object):
        model = models.CourseEnrollmentByGender
        fields = ('course_id', 'date', 'gender', 'count')


class CourseEnrollmentByEducationSerializer(BaseCourseEnrollmentModelSerializer):
    education_level = EducationLevelSerializer()

    class Meta(object):
        model = models.CourseEnrollmentByEducation
        fields = ('course_id', 'date', 'education_level', 'count')


class CourseEnrollmentByBirthYearSerializer(BaseCourseEnrollmentModelSerializer):
    class Meta(object):
        model = models.CourseEnrollmentByBirthYear
        fields = ('course_id', 'date', 'birth_year', 'count')
