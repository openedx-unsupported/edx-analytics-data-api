from django.db import models


class CourseManager(models.Manager):
    def get_by_natural_key(self, course_key):
        return self.get(course_key=course_key)
