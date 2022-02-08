# pylint: disable=line-too-long,invalid-name

import datetime
import logging

from django.core.management.base import BaseCommand

from analytics_data_api.management.commands.generate_data import (
    fake_video_ids_fallback,
    generate_all_video_data,
    generate_daily_data,
    generate_learner_engagement_data,
    generate_learner_engagement_range_data,
    generate_program_data,
    generate_tags_distribution_data,
    generate_weekly_data,
)
from analytics_data_api.v0 import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


COURSE_IDS = ['course-v1:edX+DemoX+Demo_Course', 'course-v1:edX+Insights+Stage', 'course-v1:edX+Insights+Fake+Data']
PROGRAM_COURSE_IDS = ['course-v1:edX+Insights+Stage', 'course-v1:edX+Insights+Fake+Data']


class Command(BaseCommand):
    help = 'Generate fake data for stage environment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            action='store',
            dest='database',
            default='default',
            help='Database in which to generate fake date',
        )

    def get_start_date(self, database):
        enrollments = models.CourseEnrollmentDaily.objects.using(database)
        # default to four weeks of data if no data exists
        start_date = datetime.datetime.now() - datetime.timedelta(weeks=4)
        if enrollments:
            latest_date = enrollments.latest().date
            # want to return latest date + some time difference to avoid overlap
            start_date = datetime.datetime.combine(
                latest_date + datetime.timedelta(days=1), datetime.datetime.min.time()
            )
        return start_date

    def handle(self, *args, **options):
        usernames = ['ed_xavier', 'xander_x', 'alice_bob']
        program_title = 'edX Insights'
        database = options['database']

        logger.info("Option to generate videos with ids pulled from the LMS is disabled, using fake video ids...")
        video_ids = fake_video_ids_fallback()

        start_date = self.get_start_date(database)
        end_date = datetime.datetime.now()

        for course_id in COURSE_IDS:
            logger.info("Generating data for %s in database %s", course_id, database)
            generate_weekly_data(course_id, start_date, end_date, database, delete_data=False)
            generate_daily_data(
                course_id, start_date, end_date, database,
                delete_data=False, add_birth_year=False, use_current_cumulative=True
            )
            generate_all_video_data(course_id, video_ids, database)
            for username in usernames:
                generate_learner_engagement_data(course_id, username, start_date, end_date, database)
            generate_learner_engagement_range_data(course_id, start_date.date(), end_date.date(), database)
            generate_tags_distribution_data(course_id, database)

        generate_program_data(PROGRAM_COURSE_IDS, program_title, '01n3fb1531o8470b832209243z7y421a', database)
