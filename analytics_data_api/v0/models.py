from itertools import groupby

from django.conf import settings
from django.db import models
from django.db.models import Sum
from elasticsearch_dsl import DocType, Q

from analytics_data_api.constants import country, engagement_entity_types, genders, learner


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
    cumulative_count = models.IntegerField(null=False)

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


class BaseProblemResponseAnswerDistribution(models.Model):
    """ Base model for the answer_distribution table. """

    class Meta(object):
        db_table = 'answer_distribution'
        abstract = True

    course_id = models.CharField(db_index=True, max_length=255)
    module_id = models.CharField(db_index=True, max_length=255)
    part_id = models.CharField(db_index=True, max_length=255)
    correct = models.NullBooleanField()
    value_id = models.CharField(db_index=True, max_length=255, null=True)
    answer_value = models.TextField(null=True, db_column='answer_value_text')
    variant = models.IntegerField(null=True)
    problem_display_name = models.TextField(null=True)
    question_text = models.TextField(null=True)
    created = models.DateTimeField(auto_now_add=True)


class ProblemResponseAnswerDistribution(BaseProblemResponseAnswerDistribution):
    """ Original model for the count of a particular answer to a response to a problem in a course. """

    class Meta(BaseProblemResponseAnswerDistribution.Meta):
        managed = False

    count = models.IntegerField()


class ProblemFirstLastResponseAnswerDistribution(BaseProblemResponseAnswerDistribution):
    """ Updated model for answer_distribution table with counts of first and last attempts at problems. """

    class Meta(BaseProblemResponseAnswerDistribution.Meta):
        verbose_name = 'first_last_answer_distribution'

    first_response_count = models.IntegerField()
    last_response_count = models.IntegerField()


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


class BaseVideo(models.Model):
    """ Base video model. """
    pipeline_video_id = models.CharField(db_index=True, max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    class Meta(object):
        abstract = True


class VideoTimeline(BaseVideo):
    """ Timeline of video segments. """

    segment = models.IntegerField()
    num_users = models.IntegerField()
    num_views = models.IntegerField()

    class Meta(BaseVideo.Meta):
        db_table = 'video_timeline'


class Video(BaseVideo):
    """ Videos associated with a particular course. """

    course_id = models.CharField(db_index=True, max_length=255)
    encoded_module_id = models.CharField(db_index=True, max_length=255)
    duration = models.IntegerField()
    segment_length = models.IntegerField()
    users_at_start = models.IntegerField()
    users_at_end = models.IntegerField()

    class Meta(BaseVideo.Meta):
        db_table = 'video'


class RosterEntry(DocType):
    # pylint: disable=old-style-class
    class Meta:
        index = settings.ELASTICSEARCH_LEARNERS_INDEX
        doc_type = 'roster_entry'

    @classmethod
    def get_course_user(cls, course_id, username):
        return cls.search().query('term', course_id=course_id).query(
            'term', username=username).execute()

    @classmethod
    def get_users_in_course(
            cls,
            course_id,
            segments=None,
            ignore_segments=None,
            # TODO: enable during https://openedx.atlassian.net/browse/AN-6319
            # cohort=None,
            enrollment_mode=None,
            text_search=None,
            order_by='username',
            sort_order='asc'
    ):
        """
        Construct a search query for all users in `course_id` and return
        the Search object.  Raises `ValueError` if both `segments` and
        `ignore_segments` are provided.
        """
        # Error handling
        if segments and ignore_segments:
            raise ValueError('Cannot combine `segments` and `ignore_segments` parameters.')
        for segment in (segments or list()) + (ignore_segments or list()):
            if segment not in learner.SEGMENTS:
                raise ValueError("segments/ignore_segments value '{segment}' must be one of: ({segments})".format(
                    segment=segment, segments=', '.join(learner.SEGMENTS)
                ))
        order_by_options = (
            'username', 'email', 'discussions_contributed', 'problems_attempted', 'problems_completed', 'videos_viewed'
        )
        sort_order_options = ('asc', 'desc')
        if order_by not in order_by_options:
            raise ValueError("order_by value '{order_by}' must be one of: ({order_by_options})".format(
                order_by=order_by, order_by_options=', '.join(order_by_options)
            ))
        if sort_order not in sort_order_options:
            raise ValueError("sort_order value '{sort_order}' must be one of: ({sort_order_options})".format(
                sort_order=sort_order, sort_order_options=', '.join(sort_order_options)
            ))

        search = cls.search()
        search.query = Q('bool', must=[Q('term', course_id=course_id)])

        # Filtering/Search
        if segments:
            search.query.must.append(Q('bool', should=[Q('term', segments=segment) for segment in segments]))
        elif ignore_segments:
            for segment in ignore_segments:
                search = search.query(~Q('term', segments=segment))
        # TODO: enable during https://openedx.atlassian.net/browse/AN-6319
        # if cohort:
        #     search = search.query('term', cohort=cohort)
        if enrollment_mode:
            search = search.query('term', enrollment_mode=enrollment_mode)
        if text_search:
            search.query.must.append(Q('multi_match', query=text_search, fields=['name', 'username', 'email']))

        # Sorting
        sort_term = order_by if sort_order == 'asc' else '-{}'.format(order_by)
        search = search.sort(sort_term)

        return search

    @classmethod
    def get_course_metadata(cls, course_id):
        """
        Returns the number of students belonging to particular cohorts,
        segments, and enrollment modes within a course.  Returns data in the
        following format:

        {
            'cohorts': {
                <cohort_name>: <learner_count>
            },
            'segments': {
                <segment_name>: <learner_count>
            },
            'enrollment_modes': {
                <enrollment_mode_name>: <learner_count>
            }
        }
        """
        search = cls.search()
        search.query = Q('bool', must=[Q('term', course_id=course_id)])
        search.aggs.bucket('enrollment_modes', 'terms', field='enrollment_mode')
        search.aggs.bucket('segments', 'terms', field='segments')
        # TODO: enable during https://openedx.atlassian.net/browse/AN-6319
        # search.aggs.bucket('group_by_cohorts', 'terms', field='cohort')
        response = search.execute()
        # Build up the map of aggregation name to count
        aggregations = {
            aggregation_name: {
                bucket.key: bucket.doc_count
                for bucket in response.aggregations[aggregation_name].buckets
            }
            for aggregation_name in response.aggregations
        }
        # Add default values of 0 for segments with no learners
        for segment in learner.SEGMENTS:
            if segment not in aggregations['segments']:
                aggregations['segments'][segment] = 0
        return aggregations


class ModuleEngagementTimelineManager(models.Manager):
    """
    Modifies the ModuleEngagement queryset to aggregate engagement data for
    the learner engagement timeline.
    """
    def get_timelines(self, course_id, username):
        queryset = ModuleEngagement.objects.all().filter(course_id=course_id, username=username) \
            .values('date', 'entity_type', 'event') \
            .annotate(count=Sum('count')) \
            .order_by('date')

        timelines = []

        for key, group in groupby(queryset, lambda x: (x['date'])):
            # Iterate over groups and create a single item with engagement data
            item = {
                u'date': key,
            }
            for engagement in group:
                entity_type = engagement_entity_types.SINGULAR_TO_PLURAL[engagement['entity_type']]
                engagement_type = '{}_{}'.format(entity_type, engagement['event'])
                count = item.get(engagement_type, 0)
                count += engagement['count']
                item[engagement_type] = count
            timelines.append(item)

        return timelines


class ModuleEngagement(models.Model):
    """User interactions with entities within the courseware."""

    course_id = models.CharField(db_index=True, max_length=255)
    username = models.CharField(max_length=255)
    date = models.DateTimeField()
    # This will be one of "problem", "video" or "forum"
    entity_type = models.CharField(max_length=255)
    # For problems this will be the usage key, for videos it will be the html encoded module ID,
    # for forums it will be the commentable_id
    entity_id = models.CharField(max_length=255)
    # A description of what interaction occurred, e.g. "contributed" or "viewed"
    event = models.CharField(max_length=255)
    # The number of times the user interacted with this entity in this way on this day.
    count = models.IntegerField()

    objects = ModuleEngagementTimelineManager()

    class Meta(object):
        db_table = 'module_engagement'


class ModuleEngagementMetricRanges(models.Model):
    """
    Represents the low and high values for a module engagement entity and event pair,
    known as the metric.  The range_type will either be high or low, bounded by
    low_value and high_value.
    """

    course_id = models.CharField(db_index=True, max_length=255)
    start_date = models.DateTimeField()
    # This is a left-closed interval. No data from the end_date is included in the analysis.
    end_date = models.DateTimeField()
    metric = models.CharField(max_length=50)
    range_type = models.CharField(max_length=50)
    # Also a left-closed interval, so any metric whose value is equal to the high_value
    # is not included in this range.
    high_value = models.FloatField()
    low_value = models.FloatField()

    class Meta(object):
        db_table = 'module_engagement_metric_ranges'
