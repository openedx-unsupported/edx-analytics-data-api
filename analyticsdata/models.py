
from django.db import models


class CourseActivityLastWeek(models.Model):
    db_from_setting = 'ANALYTICS_DATABASE'
    class Meta:
        db_table = 'course_activity'

    course_id = models.CharField(db_index=True, max_length=255)
    interval_start = models.DateTimeField()
    interval_end = models.DateTimeField()
    label = models.CharField(db_index=True, max_length=255)
    count = models.IntegerField()

    def __unicode__(self):
        return '{0} {1}/{2} {3}'.format(course_id, self.from_date.isoformat(), self.to_date.isoformat(), action)
