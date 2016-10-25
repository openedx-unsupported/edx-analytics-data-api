from collections import OrderedDict
from urlparse import urljoin
from django.conf import settings
from rest_framework import pagination, serializers
from rest_framework.response import Response

from analytics_data_api.constants import (
    engagement_events,
    enrollment_modes,
)
from analytics_data_api.v0 import models


# Below are the enrollment modes supported by this API.
ENROLLMENT_MODES = [enrollment_modes.AUDIT, enrollment_modes.CREDIT, enrollment_modes.HONOR,
                    enrollment_modes.PROFESSIONAL, enrollment_modes.VERIFIED]


class CourseActivityByWeekSerializer(serializers.ModelSerializer):
    """
    Representation of CourseActivityByWeek that excludes the id field.

    This table is managed by the data pipeline, and records can be removed and added at any time. The id for a
    particular record is likely to change unexpectedly so we avoid exposing it.
    """

    activity_type = serializers.SerializerMethodField()

    def get_activity_type(self, obj):
        """
        Lower-case activity type and change active to any.
        """

        activity_type = obj.activity_type.lower()
        if activity_type == 'active':
            activity_type = 'any'

        return activity_type

    class Meta(object):
        model = models.CourseActivityWeekly
        fields = ('interval_start', 'interval_end', 'activity_type', 'count', 'course_id')


class ModelSerializerWithCreatedField(serializers.ModelSerializer):
    created = serializers.DateTimeField(format=settings.DATETIME_FORMAT)


# pylint: disable=abstract-method
class ProblemSerializer(serializers.Serializer):
    """
    Serializer for problems.
    """

    module_id = serializers.CharField(required=True)
    total_submissions = serializers.IntegerField(default=0)
    correct_submissions = serializers.IntegerField(default=0)
    part_ids = serializers.ListField(child=serializers.CharField())
    created = serializers.DateTimeField(format=settings.DATETIME_FORMAT)


# pylint: disable=abstract-method
class ProblemsAndTagsSerializer(serializers.Serializer):
    """
    Serializer for problems and tags.
    """

    module_id = serializers.CharField(required=True)
    total_submissions = serializers.IntegerField(default=0)
    correct_submissions = serializers.IntegerField(default=0)
    tags = serializers.SerializerMethodField()
    created = serializers.DateTimeField(format=settings.DATETIME_FORMAT)

    def get_tags(self, obj):
        return obj.get('tags', None)


class ProblemResponseAnswerDistributionSerializer(ModelSerializerWithCreatedField):
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
            'answer_value',
            'problem_display_name',
            'question_text',
            'variant',
            'created'
        )


class ConsolidatedAnswerDistributionSerializer(ProblemResponseAnswerDistributionSerializer):
    """
    Serializer for consolidated answer distributions.
    """

    consolidated_variant = serializers.BooleanField()

    class Meta(ProblemResponseAnswerDistributionSerializer.Meta):
        fields = ProblemResponseAnswerDistributionSerializer.Meta.fields + ('consolidated_variant',)

    # pylint: disable=super-on-old-class
    def restore_object(self, attrs, instance=None):
        """
        Pops and restores non-model field.
        """

        consolidated_variant = attrs.pop('consolidated_variant', None)
        distribution = super(ConsolidatedAnswerDistributionSerializer, self).restore_object(attrs, instance)
        distribution.consolidated_variant = consolidated_variant

        return distribution


class ProblemFirstLastResponseAnswerDistributionSerializer(ProblemResponseAnswerDistributionSerializer):
    """
    Serializer for answer distribution table including counts of first and last response values.
    """

    class Meta(ProblemResponseAnswerDistributionSerializer.Meta):
        model = models.ProblemFirstLastResponseAnswerDistribution
        fields = ProblemResponseAnswerDistributionSerializer.Meta.fields + (
            'first_response_count',
            'last_response_count',
        )

        fields = tuple([field for field in fields if field != 'count'])


class ConsolidatedFirstLastAnswerDistributionSerializer(ProblemFirstLastResponseAnswerDistributionSerializer):
    """
    Serializer for consolidated answer distributions including first attempt counts.
    """

    consolidated_variant = serializers.BooleanField()

    class Meta(ProblemFirstLastResponseAnswerDistributionSerializer.Meta):
        fields = ProblemFirstLastResponseAnswerDistributionSerializer.Meta.fields + ('consolidated_variant',)

    # pylint: disable=super-on-old-class
    def restore_object(self, attrs, instance=None):
        """
        Pops and restores non-model field.
        """

        consolidated_variant = attrs.pop('consolidated_variant', None)
        distribution = super(ConsolidatedFirstLastAnswerDistributionSerializer, self).restore_object(attrs, instance)
        distribution.consolidated_variant = consolidated_variant

        return distribution


class GradeDistributionSerializer(ModelSerializerWithCreatedField):
    """
    Representation of the grade_distribution table without id
    """

    class Meta(object):
        model = models.GradeDistribution
        fields = (
            'module_id',
            'course_id',
            'grade',
            'max_grade',
            'count',
            'created'
        )


class SequentialOpenDistributionSerializer(ModelSerializerWithCreatedField):
    """
    Representation of the sequential_open_distribution table without id
    """

    class Meta(object):
        model = models.SequentialOpenDistribution
        fields = (
            'module_id',
            'course_id',
            'count',
            'created'
        )


class BaseCourseEnrollmentModelSerializer(ModelSerializerWithCreatedField):
    date = serializers.DateField(format=settings.DATE_FORMAT)


class CourseEnrollmentDailySerializer(BaseCourseEnrollmentModelSerializer):
    """ Representation of course enrollment for a single day and course. """

    class Meta(object):
        model = models.CourseEnrollmentDaily
        fields = ('course_id', 'date', 'count', 'created')


class CourseEnrollmentModeDailySerializer(BaseCourseEnrollmentModelSerializer):
    """ Representation of course enrollment, broken down by mode, for a single day and course. """
    audit = serializers.SerializerMethodField()
    credit = serializers.SerializerMethodField()
    honor = serializers.SerializerMethodField()
    professional = serializers.SerializerMethodField()
    verified = serializers.SerializerMethodField()

    def get_audit(self, obj):
        return obj.get('audit', 0)

    def get_honor(self, obj):
        return obj.get('honor', 0)

    def get_credit(self, obj):
        return obj.get('credit', 0)

    def get_professional(self, obj):
        return obj.get('professional', 0)

    def get_verified(self, obj):
        return obj.get('verified', 0)

    class Meta(object):
        model = models.CourseEnrollmentModeDaily

        # Declare the dynamically-created fields here as well so that they will be picked up by Swagger.
        fields = ['course_id', 'date', 'count', 'cumulative_count', 'created'] + ENROLLMENT_MODES


# pylint: disable=abstract-method
class CountrySerializer(serializers.Serializer):
    """
    Serialize country to an object with fields for the complete country name
    and the ISO-3166 two- and three-digit codes.

    Some downstream consumers need two-digit codes, others need three. Both are provided to avoid the need
    for conversion.
    """
    alpha2 = serializers.CharField()
    alpha3 = serializers.CharField()
    name = serializers.CharField()


class CourseEnrollmentByCountrySerializer(BaseCourseEnrollmentModelSerializer):
    # pylint: disable=unexpected-keyword-arg, no-value-for-parameter
    country = CountrySerializer(many=False)

    class Meta(object):
        model = models.CourseEnrollmentByCountry
        fields = ('date', 'course_id', 'country', 'count', 'created')


class CourseEnrollmentByGenderSerializer(BaseCourseEnrollmentModelSerializer):

    female = serializers.ReadOnlyField()
    male = serializers.ReadOnlyField()
    other = serializers.ReadOnlyField()
    unknown = serializers.ReadOnlyField()

    def get_female(self, obj):
        return obj.get('female', None)

    def get_male(self, obj):
        return obj.get('male', None)

    def get_other(self, obj):
        return obj.get('other', None)

    def get_unknown(self, obj):
        return obj.get('unknown', None)

    class Meta(object):
        model = models.CourseEnrollmentByGender
        fields = ('course_id', 'date', 'female', 'male', 'other', 'unknown', 'created')


class CourseEnrollmentByEducationSerializer(BaseCourseEnrollmentModelSerializer):
    class Meta(object):
        model = models.CourseEnrollmentByEducation
        fields = ('course_id', 'date', 'education_level', 'count', 'created')


class CourseEnrollmentByBirthYearSerializer(BaseCourseEnrollmentModelSerializer):
    class Meta(object):
        model = models.CourseEnrollmentByBirthYear
        fields = ('course_id', 'date', 'birth_year', 'count', 'created')


class CourseActivityWeeklySerializer(serializers.ModelSerializer):
    interval_start = serializers.DateTimeField(format=settings.DATETIME_FORMAT)
    interval_end = serializers.DateTimeField(format=settings.DATETIME_FORMAT)
    any = serializers.IntegerField(required=False)
    attempted_problem = serializers.IntegerField(required=False)
    played_video = serializers.IntegerField(required=False)
    posted_forum = serializers.IntegerField(required=False)
    created = serializers.DateTimeField(format=settings.DATETIME_FORMAT)

    class Meta(object):
        model = models.CourseActivityWeekly
        fields = ('interval_start', 'interval_end', 'course_id', 'any', 'attempted_problem', 'played_video',
                  'posted_forum', 'created')


class VideoSerializer(ModelSerializerWithCreatedField):
    class Meta(object):
        model = models.Video
        fields = (
            'pipeline_video_id',
            'encoded_module_id',
            'duration',
            'segment_length',
            'users_at_start',
            'users_at_end',
            'created'
        )


class VideoTimelineSerializer(ModelSerializerWithCreatedField):
    class Meta(object):
        model = models.VideoTimeline
        fields = (
            'segment',
            'num_users',
            'num_views',
            'created'
        )


# pylint: disable=abstract-method
class LastUpdatedSerializer(serializers.Serializer):
    last_updated = serializers.DateTimeField(source='date', format=settings.DATE_FORMAT)


# pylint: disable=abstract-method
class LearnerSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    enrollment_mode = serializers.CharField()
    name = serializers.CharField()
    account_url = serializers.SerializerMethodField()
    email = serializers.CharField()
    language = serializers.CharField()
    location = serializers.CharField()
    year_of_birth = serializers.IntegerField()
    level_of_education = serializers.CharField()
    gender = serializers.CharField()
    mailing_address = serializers.CharField()
    city = serializers.CharField()
    country = serializers.CharField()
    goals = serializers.CharField()
    segments = serializers.SerializerMethodField()
    engagements = serializers.SerializerMethodField()
    enrollment_date = serializers.DateTimeField(format=settings.DATE_FORMAT)
    cohort = serializers.SerializerMethodField()

    def get_segments(self, obj):
        # using hasattr() instead because DocType.get() is overloaded and makes a request
        if hasattr(obj, 'segments'):
            # json parsing will fail unless in unicode
            return [unicode(segment) for segment in obj.segments]
        else:
            return []

    def get_cohort(self, obj):
        # using hasattr() instead because DocType.get() is overloaded and makes a request
        if hasattr(obj, 'cohort') and len(obj.cohort) > 0:
            return obj.cohort
        else:
            return None

    def get_account_url(self, obj):
        if settings.LMS_USER_ACCOUNT_BASE_URL:
            return urljoin(settings.LMS_USER_ACCOUNT_BASE_URL, obj.username)
        else:
            return None

    def default_if_none(self, value, default=0):
        return value if value is not None else default

    def get_engagements(self, obj):
        """
        Add the engagement totals.
        """
        engagements = {}

        # fill in these fields will 0 if values not returned/found
        default_if_none_fields = ['discussion_contributions', 'problems_attempted',
                                  'problems_completed', 'videos_viewed']
        for field in default_if_none_fields:
            engagements[field] = self.default_if_none(getattr(obj, field, None), 0)

        # preserve null values for problem attempts per completed
        engagements['problem_attempts_per_completed'] = getattr(obj, 'problem_attempts_per_completed', None)

        return engagements


class EdxPaginationSerializer(pagination.PageNumberPagination):
    """
    Adds values to the response according to edX REST API Conventions.
    """
    page_size_query_param = 'page_size'
    page_size = getattr(settings, 'DEFAULT_PAGE_SIZE', 25)
    max_page_size = getattr(settings, 'MAX_PAGE_SIZE', 100)  # TODO -- tweak during load testing

    def get_paginated_response(self, data):
        # The output is more readable with num_pages included not at the end, but
        # inefficient to insert into an OrderedDict, so the response is copied from
        # rest_framework.pagination with the addition of "num_pages".
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('num_pages', self.page.paginator.num_pages),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


# pylint: disable=abstract-method
class EngagementDaySerializer(serializers.Serializer):
    date = serializers.DateField(format=settings.DATE_FORMAT)
    problems_attempted = serializers.SerializerMethodField()
    problems_completed = serializers.SerializerMethodField()
    discussion_contributions = serializers.SerializerMethodField()
    videos_viewed = serializers.SerializerMethodField()

    def get_problems_attempted(self, obj):
        return obj.get('problems_attempted', 0)

    def get_problems_completed(self, obj):
        return obj.get('problems_completed', 0)

    def get_discussion_contributions(self, obj):
        return obj.get('discussion_contributions', 0)

    def get_videos_viewed(self, obj):
        return obj.get('videos_viewed', 0)


# pylint: disable=abstract-method
class DateRangeSerializer(serializers.Serializer):
    start = serializers.DateField(source='start_date', format=settings.DATE_FORMAT)
    end = serializers.DateField(source='end_date', format=settings.DATE_FORMAT)


# pylint: disable=abstract-method
class EnagementRangeMetricSerializer(serializers.Serializer):
    """
    Serializes ModuleEngagementMetricRanges ('bottom', 'average', and 'top') into
    the class_rank_bottom, class_rank_average, and class_rank_top ranges
    represented as arrays. If any one of the ranges is not defined, it is not
    included in the serialized output.
    """
    class_rank_bottom = serializers.SerializerMethodField()
    class_rank_average = serializers.SerializerMethodField()
    class_rank_top = serializers.SerializerMethodField()

    def get_class_rank_average(self, obj):
        return self._transform_range(obj['average'])

    def get_class_rank_bottom(self, obj):
        return self._transform_range(obj['bottom'])

    def get_class_rank_top(self, obj):
        return self._transform_range(obj['top'])

    def _transform_range(self, metric_range):
        return [metric_range.low_value, metric_range.high_value] if metric_range else None


# pylint: disable=abstract-method
class CourseLearnerMetadataSerializer(serializers.Serializer):
    enrollment_modes = serializers.ReadOnlyField(source='es_data.enrollment_modes')
    segments = serializers.ReadOnlyField(source='es_data.segments')
    cohorts = serializers.ReadOnlyField(source='es_data.cohorts')
    engagement_ranges = serializers.SerializerMethodField()

    def get_engagement_ranges(self, obj):
        query_set = obj['engagement_ranges']
        engagement_ranges = {
            'date_range': DateRangeSerializer(query_set[0] if len(query_set) else None).data
        }

        for metric in engagement_events.EVENTS:
            # construct the range type to class rank pairs
            ranges_ranks = [('normal', 'average')]
            if metric == 'problem_attempts_per_completed':
                ranges_ranks.extend([('low', 'top'), ('high', 'bottom')])
            else:
                ranges_ranks.extend([('high', 'top'), ('low', 'bottom')])

            # put together data to be serialized
            serializer_kwargs = {}
            for range_type, class_rank_type in ranges_ranks:
                range_queryset = query_set.filter(metric=metric, range_type=range_type)
                serializer_kwargs[class_rank_type] = range_queryset[0] if len(range_queryset) else None
            engagement_ranges.update({
                metric: EnagementRangeMetricSerializer(serializer_kwargs).data
            })

        return engagement_ranges
