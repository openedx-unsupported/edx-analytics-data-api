from django.core.management import call_command
from django.test import TestCase

from analytics_data_api.tests.test_utils import set_databases
from analytics_data_api.v0 import models


@set_databases
class GenerateFakeCourseDataTests(TestCase):
    def testNormalRun(self):
        num_weeks = 2
        course_id = "edX/DemoX/Demo_Course"

        call_command(
            'generate_fake_course_data',
            f"--num-weeks={num_weeks}",
            "--no-videos",
            "--course-id", course_id,
            "--database", 'analytics',
        )

        for model in [models.CourseEnrollmentDaily,
                      models.CourseEnrollmentModeDaily,
                      models.CourseEnrollmentByGender,
                      models.CourseEnrollmentByEducation,
                      models.CourseEnrollmentByBirthYear,
                      models.CourseEnrollmentByCountry,
                      models.CourseMetaSummaryEnrollment,
                      models.CourseProgramMetadata]:
            self.assertTrue(model.objects.filter(course_id=course_id, ).exists())
            self.assertEqual(model.objects.filter(course_id=course_id).count(), model.objects.all().count())
