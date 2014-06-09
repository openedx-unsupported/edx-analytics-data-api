
from django.db import models
from rest_framework import serializers


class CourseActivityByWeek(models.Model):

    """A count of unique users who performed a particular action during a week."""

    db_from_setting = 'ANALYTICS_DATABASE'

    class Meta:  # pylint: disable=old-style-class
        db_table = 'course_activity'

    course_id = models.CharField(db_index=True, max_length=255)
    interval_start = models.DateTimeField()
    interval_end = models.DateTimeField()
    label = models.CharField(db_index=True, max_length=255)
    count = models.IntegerField()

    @classmethod
    def get_most_recent(cls, course_id, label):
        """Activity for the week that was mostly recently computed."""
        return cls.objects.filter(course_id=course_id, label=label).latest('interval_end')


class CourseActivityByWeekSerializer(serializers.ModelSerializer):

    """
    Representation of CourseActivityByWeek that excludes the id field.

    This table is managed by the data pipeline, and records can be removed and added at any time. The id for a
    particular record is likely to change unexpectedly so we avoid exposing it.
    """

    class Meta:  # pylint: disable=old-style-class
        model = CourseActivityByWeek
        fields = ('course_id', 'interval_start', 'interval_end', 'label', 'count')
