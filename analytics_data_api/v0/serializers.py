import json
import re
from collections import OrderedDict

import html5lib
from django.conf import settings
from rest_framework import pagination, serializers
from rest_framework.response import Response

from analytics_data_api.constants import enrollment_modes
from analytics_data_api.v0 import models

# Below are the enrollment modes supported by this API.
ENROLLMENT_MODES = [enrollment_modes.AUDIT, enrollment_modes.CREDIT, enrollment_modes.HONOR,
                    enrollment_modes.PROFESSIONAL, enrollment_modes.VERIFIED, enrollment_modes.MASTERS]


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

    class Meta:
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

    class Meta:
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['answer_value'] = self._clean_answer_string(data['answer_value'])
        data['value_id'] = self._clean_answer_string(data['value_id'])
        return data

    def _clean_answer_string(self, answer_value):
        """
        Convert value to a canonical string representation.
        If value is a list, then returns list values
        surrounded by square brackets and delimited by pipes
        (e.g. "[choice_1|choice_3|choice_4]").
        If value is a string, just returns as-is.
        If the value contains html the answer_string is parsed as XML,
        and the text value of the answer_value is returned.
        """

        def normalize(value):
            """Pull out HTML tags and deslugify certain escape sequences."""
            text = self._get_text_from_html(value)
            return self._parse_slugged_slashes(text)

        # attempt to evaluate string as a list (this will get special
        # formatting), else keep it a string
        try:
            answer_eval = json.loads(answer_value.encode('unicode_escape'))
            if isinstance(answer_eval, list):
                answer_value = answer_eval
        except Exception:  # pylint: disable=broad-except
            pass

        # produce a string, or 'list' of strings as output
        # lists containing non-string values such as dictionaries will have
        # those elements represented as JSON strings
        if isinstance(answer_value, str):
            return normalize(answer_value)
        if isinstance(answer_value, list):
            normalized = []
            for value in answer_value:
                if isinstance(value, str):
                    normalized.append(normalize(value))
                else:
                    normalized.append(json.dumps(value))
            return u'[{list_val}]'.format(list_val=u'|'.join(normalized))

        return str(answer_value)

    def _get_text_from_html(self, markup):
        """
        Convert html markup to plain text.
        Includes stripping excess whitespace, and assuring whitespace
        exists between elements (e.g. table elements).
        """
        try:
            root = html5lib.parse(markup)
            text_list = []
            for val in self._get_text_from_element(root):
                text_list.extend(val.strip().split(' '))
            text = u' '.join(text_list)
        except Exception:  # pylint: disable=broad-except
            text = ''

        return text

    def _get_text_from_element(self, node):
        """Traverse ElementTree node recursively to return text values."""
        tag = node.tag
        if not isinstance(tag, str) and tag is not None:
            return
        if node.text:
            yield node.text
        for child in node:
            for text in self._get_text_from_element(child):
                yield text
            if child.tail:
                yield child.tail

    def _parse_slugged_slashes(self, text):
        """
        Data coming out of snowflake sometimes looks like "**FOURBACKSLASHQUOTE** something" because of
        slugging from
        https://github.com/edx/warehouse-transforms/blob/master/projects/automated/raw_to_source/models/downstream_sources/tracking_log_events/tracking_events.sql
        we need to remove the slugs so that it is consumable/readable in insights.
        """
        # order matters if a we have a key that is a substring of another key
        # this is not the case right now but use an ordered dict so results are deterministic
        replacements = OrderedDict({
            '**FOURBACKSLASHQUOTE**': '\\\\\\\\"',
            '**THREEBACKSLASHQUOTE**': '\\\\\\"',
            '**TWOBACKSLASHQUOTE**': '\\\\"',
            '**ONEBACKSLASHQUOTE**': '\\"',
            '**TWOBACKSLASH**': '\\\\',
            '**BACKSLASHSPACE**': '\\ ',
            '**BACKSLASHQUOTE**': '\\"',
        })

        # escape the '*' characters and build one big regex OR pattern
        escaped_replace = map(re.escape, replacements)
        pattern = re.compile("|".join(escaped_replace))

        # for each match in the pattern replace with the value from the replacement dictionary
        return pattern.sub(lambda match: replacements[match.group(0)], text)


class ConsolidatedAnswerDistributionSerializer(ProblemResponseAnswerDistributionSerializer):
    """
    Serializer for consolidated answer distributions.
    """

    consolidated_variant = serializers.BooleanField()

    class Meta(ProblemResponseAnswerDistributionSerializer.Meta):
        fields = ProblemResponseAnswerDistributionSerializer.Meta.fields + ('consolidated_variant',)

    def restore_object(self, attrs, instance=None):
        """
        Pops and restores non-model field.
        """

        consolidated_variant = attrs.pop('consolidated_variant', None)
        distribution = super().restore_object(attrs, instance)
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

    def restore_object(self, attrs, instance=None):
        """
        Pops and restores non-model field.
        """

        consolidated_variant = attrs.pop('consolidated_variant', None)
        distribution = super().restore_object(attrs, instance)
        distribution.consolidated_variant = consolidated_variant

        return distribution


class GradeDistributionSerializer(ModelSerializerWithCreatedField):
    """
    Representation of the grade_distribution table without id
    """

    class Meta:
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

    class Meta:
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

    class Meta:
        model = models.CourseEnrollmentDaily
        fields = ('course_id', 'date', 'count', 'created')


class CourseEnrollmentModeDailySerializer(BaseCourseEnrollmentModelSerializer):
    """ Representation of course enrollment, broken down by mode, for a single day and course. """
    audit = serializers.SerializerMethodField()
    credit = serializers.SerializerMethodField()
    honor = serializers.SerializerMethodField()
    professional = serializers.SerializerMethodField()
    verified = serializers.SerializerMethodField()
    masters = serializers.SerializerMethodField()

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

    def get_masters(self, obj):
        return obj.get('masters', 0)

    class Meta:
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

    class Meta:
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

    class Meta:
        model = models.CourseEnrollmentByGender
        fields = ('course_id', 'date', 'female', 'male', 'other', 'unknown', 'created')


class CourseEnrollmentByEducationSerializer(BaseCourseEnrollmentModelSerializer):
    class Meta:
        model = models.CourseEnrollmentByEducation
        fields = ('course_id', 'date', 'education_level', 'count', 'created')


class CourseEnrollmentByBirthYearSerializer(BaseCourseEnrollmentModelSerializer):
    class Meta:
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

    class Meta:
        model = models.CourseActivityWeekly
        fields = ('interval_start', 'interval_end', 'course_id', 'any', 'attempted_problem', 'played_video',
                  'posted_forum', 'created')


class VideoSerializer(ModelSerializerWithCreatedField):
    class Meta:
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
    class Meta:
        model = models.VideoTimeline
        fields = (
            'segment',
            'num_users',
            'num_views',
            'created'
        )


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


class EnterpriseLearnerEngagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ModuleEngagement
        fields = '__all__'


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
class UserEngagementSerializer(serializers.Serializer):
    """
    Serializes row data from module_engagement
    """
    username = serializers.CharField()
    videos_overall = serializers.IntegerField()
    videos_last_week = serializers.IntegerField()
    problems_overall = serializers.IntegerField()
    problems_last_week = serializers.IntegerField()
    correct_problems_overall = serializers.IntegerField()
    correct_problems_last_week = serializers.IntegerField()
    problems_attempts_overall = serializers.IntegerField()
    problems_attempts_last_week = serializers.IntegerField()
    forum_posts_overall = serializers.IntegerField()
    forum_posts_last_week = serializers.IntegerField()
    date_last_active = serializers.DateTimeField(format=settings.DATE_FORMAT)


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes additional `fields` and/or `exclude` keyword arguments that control which
    fields should be displayed.

    Blatantly taken from http://www.django-rest-framework.org/api-guide/serializers/#dynamically-modifying-fields

    If a field name is specified in both `fields` and `exclude`, then the exclude option takes precedence and the field
    will not be included in the serialized result.

    Keyword Arguments:
        fields  -- list of field names on the model to include in the serialized result
        exclude -- list of field names on the model to exclude in the serialized result
    """

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)
        exclude = kwargs.pop('exclude', None)

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

        if exclude is not None:
            # Drop any fields that are specified in the `exclude` argument.
            disallowed = set(exclude)
            existing = set(self.fields.keys())
            for field_name in existing & disallowed:  # intersection
                self.fields.pop(field_name)


class CourseMetaSummaryEnrollmentSerializer(ModelSerializerWithCreatedField, DynamicFieldsModelSerializer):
    """
    Serializer for course and enrollment counts per mode.
    """
    course_id = serializers.CharField()
    catalog_course_title = serializers.CharField()
    catalog_course = serializers.CharField()
    start_date = serializers.DateTimeField(source='start_time', format=settings.DATETIME_FORMAT)
    end_date = serializers.DateTimeField(source='end_time', format=settings.DATETIME_FORMAT)
    pacing_type = serializers.CharField()
    availability = serializers.CharField()
    count = serializers.IntegerField(default=0)
    cumulative_count = serializers.IntegerField(default=0)
    count_change_7_days = serializers.IntegerField(default=0)
    recent_count_change = serializers.IntegerField(default=None)
    passing_users = serializers.IntegerField(default=0)
    enrollment_modes = serializers.SerializerMethodField()
    programs = serializers.SerializerMethodField()

    def get_enrollment_modes(self, obj):
        return obj.get('enrollment_modes', None)

    def get_programs(self, obj):
        return obj.get('programs', None)

    class Meta:
        model = models.CourseMetaSummaryEnrollment
        # start_date and end_date used instead of start_time and end_time
        exclude = ('id', 'start_time', 'end_time', 'enrollment_mode')


class CourseProgramMetadataSerializer(DynamicFieldsModelSerializer):
    """
    Serializer for course and the programs it is under.
    """
    program_id = serializers.CharField()
    program_type = serializers.CharField()
    program_title = serializers.CharField()
    course_ids = serializers.SerializerMethodField()

    def get_course_ids(self, obj):
        return obj.get('course_ids', None)

    class Meta:
        model = models.CourseProgramMetadata
        # excluding course-related fields because the serialized output will be embedded in a course object
        # with those fields already defined
        exclude = ('id', 'course_id')
