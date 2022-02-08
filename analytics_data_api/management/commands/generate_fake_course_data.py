# pylint: disable=line-too-long,invalid-name

import datetime
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics_data_api.management.commands.generate_data import (
    fake_video_ids_fallback,
    fetch_videos_from_course_blocks,
    generate_all_video_data,
    generate_daily_data,
    generate_learner_engagement_data,
    generate_learner_engagement_range_data,
    generate_program_data,
    generate_tags_distribution_data,
    generate_weekly_data,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate fake data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--num-weeks',
            action='store',
            type=int,
            dest='num_weeks',
            help='Number of weeks worth of data to generate.',
        )
        parser.add_argument(
            '--course-id',
            action='store',
            dest='course_id',
            default='course-v1:edX+DemoX+Demo_Course',
            help='Course ID for which to generate fake data',
        )
        parser.add_argument(
            '--username',
            action='store',
            dest='username',
            default='ed_xavier',
            help='Username for which to generate fake data',
        )
        parser.add_argument(
            '--no-videos',
            action='store_false',
            dest='videos',
            default=True,
            help='Disables pulling video ids from the LMS server to generate fake video data and instead uses fake ids.'
        )
        parser.add_argument(
            '--database',
            action='store',
            dest='database',
            default='default',
            help='Database in which to generate fake date',
        )

    def handle(self, *args, **options):
        course_id = options['course_id']
        username = options['username']
        videos = options['videos']
        database = options['database']
        if videos:
            video_ids = fetch_videos_from_course_blocks(course_id)
            if not video_ids:
                logger.warning("Falling back to fake video id due to Course Blocks API failure...")
                video_ids = fake_video_ids_fallback()
        else:
            logger.info("Option to generate videos with ids pulled from the LMS is disabled, using fake video ids...")
            video_ids = fake_video_ids_fallback()
        start_date = timezone.now() - datetime.timedelta(weeks=10)

        num_weeks = options['num_weeks']
        if num_weeks:
            end_date = start_date + datetime.timedelta(weeks=num_weeks)
        else:
            end_date = timezone.now().replace(microsecond=0)

        logger.info("Generating data for %s in database %s", course_id, database)

        generate_weekly_data(course_id, start_date, end_date, database)
        generate_daily_data(course_id, start_date, end_date, database)
        generate_program_data([course_id], 'Demo Program', 'Demo_Program', database)
        generate_all_video_data(course_id, video_ids, database)
        generate_learner_engagement_data(course_id, username, start_date, end_date, database)
        generate_learner_engagement_range_data(course_id, start_date.date(), end_date.date(), database)
        generate_tags_distribution_data(course_id, database)
