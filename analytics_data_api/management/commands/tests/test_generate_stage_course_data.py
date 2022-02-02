import datetime

from django.core.management import call_command
from django.test import TestCase
from freezegun import freeze_time

from analytics_data_api.management.commands.generate_stage_course_data import COURSE_IDS, PROGRAM_COURSE_IDS
from analytics_data_api.tests.test_utils import set_databases
from analytics_data_api.v0 import models


@set_databases
class GenerateStageCourseDataTests(TestCase):

    def test_run_with_no_preexisting_data(self):
        """
        Test that data is generated for the past four weeks
        """

        call_command(
            'generate_stage_course_data',
            f"--database", 'analytics',
        )

        for model in [models.CourseEnrollmentDaily,
                      models.CourseEnrollmentModeDaily,
                      models.CourseEnrollmentByGender,
                      models.CourseEnrollmentByEducation,
                      models.CourseEnrollmentByCountry,
                      models.CourseMetaSummaryEnrollment]:
            for course_id in COURSE_IDS:
                self.assertTrue(model.objects.filter(course_id=course_id).exists())

                if model != models.CourseMetaSummaryEnrollment:
                    # course meta summary generates a wider date range of data
                    earliest_date = model.objects.filter(course_id=course_id).earliest('date').date
                    self.assertEqual(earliest_date, datetime.date.today() - datetime.timedelta(weeks=4))

        # check that Insights courses are in program table, while demo course is not
        for course_id in COURSE_IDS:
            if course_id in PROGRAM_COURSE_IDS:
                self.assertTrue(
                    models.CourseProgramMetadata.objects.filter(course_id=course_id).exists()
                )
            else:
                self.assertFalse(
                    models.CourseProgramMetadata.objects.filter(course_id=course_id).exists()
                )

        self.assertFalse(models.CourseEnrollmentByBirthYear.objects.exists())

    def test_run_with_preexisting_data(self):
        """
        Test that data is generated for the time between preexisting data and now,
        e.g. if data was added a week ago, should only add a weeks worth of data.
        No previous data should be deleted.
        """

        start_date = datetime.date.today() - datetime.timedelta(weeks=6)
        end_date = datetime.date.today()

        # call command first time to generate data
        with freeze_time(datetime.date.today() - datetime.timedelta(weeks=2)):
            call_command(
                'generate_stage_course_data',
                f"--database", 'analytics',
            )
        test_enrollment = models.CourseEnrollmentDaily.objects\
            .filter(course_id='course-v1:edX+DemoX+Demo_Course').earliest('date')

        # go ahead two weeks to generate data
        call_command(
            'generate_stage_course_data',
            f"--database", 'analytics',
        )

        for model in [models.CourseEnrollmentDaily,
                      models.CourseEnrollmentModeDaily,
                      models.CourseEnrollmentByGender,
                      models.CourseEnrollmentByEducation,
                      models.CourseEnrollmentByCountry,
                      models.CourseMetaSummaryEnrollment]:
            for course_id in COURSE_IDS:
                self.assertTrue(model.objects.filter(course_id=course_id).exists())

                if model != models.CourseMetaSummaryEnrollment:
                    # course meta summary generates a wider date range of data
                    earliest_date = model.objects.filter(course_id=course_id).earliest('date').date
                    self.assertEqual(earliest_date, start_date)

        # assert that old data wasn't deleted
        self.assertEqual(test_enrollment.count, models.CourseEnrollmentDaily.objects.get(id=test_enrollment.id).count)

        # assert that date range is covered
        check_date = start_date
        time_delta = datetime.timedelta(days=1)

        while check_date <= end_date:
            enrollment_objs = models.CourseEnrollmentDaily.objects.filter(
                course_id='course-v1:edX+DemoX+Demo_Course', date=check_date
            )
            self.assertEqual(len(enrollment_objs), 1)
            check_date += time_delta
