from django.db import models


class CourseManager(models.Manager):
    def get_by_natural_key(self, course_id):
        return self.get(course_id=course_id)
