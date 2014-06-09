
from django.db import models


class CourseUserActivityByWeek(models.Model):
    db_from_setting = 'ANALYTICS_DATABASE'
    class Meta:
        db_table = 'course_user_activity_by_week'

    course_id = models.CharField(db_index=True, max_length=255)
    from_date = models.DateTimeField()
    to_date = models.DateTimeField()
    action = models.IntegerField()
    count = models.IntegerField()

    def __unicode__(self):
        return '{0} {1}/{2} {3}'.format(course_id, self.from_date.isoformat(), self.to_date.isoformat(), action)
