# pylint: disable=line-too-long,invalid-name
"""
Abstract base management command meant to be called by other commands that generate fake data
"""

import datetime
import logging
import math
import random

from django.conf import settings
from django.utils import timezone
from tqdm import tqdm

from analytics_data_api.constants import engagement_events
from analytics_data_api.v0 import models
from analyticsdataserver.clients import CourseBlocksApiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# http://stackoverflow.com/a/3590105
def _constrained_sum_sample_pos(num_values, total):
    """
    Return a randomly chosen list of n positive integers summing to total.
    Each such list is equally likely to occur.
    """

    dividers = sorted(random.sample(range(1, total), num_values - 1))
    return [a - b for a, b in zip(dividers + [total], [0] + dividers)]


def _get_count(base):
    """
    Generate random count, used for adding a daily total to enrollments data
    """
    delta = 25 * random.gauss(0, 1)
    return int(base + delta)


GENDER_RATIOS = {
    'm': 0.6107,
    'f': 0.3870,
    'o': 0.23
}

EDUCATION_LEVEL_RATIOS = {
    'associates': 0.058,
    'bachelors': 0.3355,
    'primary': 0.0046,
    'secondary': 0.2442,
    'junior_secondary': 0.0286,
    'masters': 0.2518,
    'none': 0.0032,
    'other': 0.0271,
    'doctorate': 0.0470
}

COUNTRY_RATIOS = {
    'US': 0.33,
    'GH': 0.12,
    'IN': 0.10,
    'CA': 0.14,
    'CN': 0.22,
    'DE': 0.08,
    'UNKNOWN': 0.01
}

ENROLLMENT_MODE_RATIOS = {
    'audit': 0.15,
    'credit': 0.15,
    'honor': 0.25,
    'professional': 0.10,
    'verified': 0.35
}

# Generate birth year ratios
birth_years_range = list(range(1960, 2005))
ratios = [n / 1000.0 for n in _constrained_sum_sample_pos(len(birth_years_range), 1000)]
BIRTH_YEARS = dict(list(zip(birth_years_range, ratios)))


def _generate_day(date, course_id, daily_total, cumulative_count, database, add_birth_year):
    """
    Generate one day's worth of enrollment data
    """
    daily_total = _get_count(daily_total)
    models.CourseEnrollmentDaily.objects.using(database).create(course_id=course_id,
                                                                date=date, count=daily_total)

    for mode, ratio in ENROLLMENT_MODE_RATIOS.items():
        count = int(ratio * daily_total)
        cumulative_count = max(cumulative_count + 10, count)
        models.CourseEnrollmentModeDaily.objects.using(database).create(course_id=course_id, date=date,
                                                                        count=count,
                                                                        cumulative_count=cumulative_count,
                                                                        mode=mode)

    for gender, ratio in GENDER_RATIOS.items():
        count = int(ratio * daily_total)
        models.CourseEnrollmentByGender.objects.using(database).create(course_id=course_id, date=date,
                                                                       count=count, gender=gender)

    for education_level, ratio in EDUCATION_LEVEL_RATIOS.items():
        count = int(ratio * daily_total)
        models.CourseEnrollmentByEducation.objects.using(database).create(course_id=course_id, date=date,
                                                                          count=count,
                                                                          education_level=education_level)

    for country_code, ratio in COUNTRY_RATIOS.items():
        count = int(ratio * daily_total)
        models.CourseEnrollmentByCountry.objects.using(database).create(course_id=course_id, date=date,
                                                                        count=count,
                                                                        country_code=country_code)
    if add_birth_year:
        for birth_year, ratio in BIRTH_YEARS.items():
            count = int(ratio * daily_total)
            models.CourseEnrollmentByBirthYear.objects.using(database).create(course_id=course_id, date=date,
                                                                              count=count,
                                                                              birth_year=birth_year)


def generate_daily_data(course_id, start_date, end_date, database,
                        delete_data=True, add_birth_year=True, use_current_cumulative=False):
    if delete_data:
        # Delete existing data
        for model in [models.CourseEnrollmentDaily,
                      models.CourseEnrollmentModeDaily,
                      models.CourseEnrollmentByGender,
                      models.CourseEnrollmentByEducation,
                      models.CourseEnrollmentByBirthYear,
                      models.CourseEnrollmentByCountry,
                      models.CourseProgramMetadata]:
            model.objects.using(database).all().delete()

        logger.info("Deleted all daily course enrollment data.")
        logger.info("Generating new daily course enrollment data...")

    logger.info("Generating new daily course enrollment data...")

    # Create new data
    daily_total = 1500
    date = start_date

    enrollment_objs = models.CourseEnrollmentModeDaily.objects.using(database).filter(course_id=course_id)
    # start incrementing cumulative count, as opposed to starting from 0 every time we run the command
    cumulative_count = enrollment_objs.latest().cumulative_count \
        if (use_current_cumulative and enrollment_objs) \
        else 0

    progress = tqdm(total=(end_date - date).days + 2)
    while date <= end_date:
        _generate_day(date, course_id, daily_total, cumulative_count, database, add_birth_year)
        progress.update(1)
        date = date + datetime.timedelta(days=1)

    models.CourseMetaSummaryEnrollment.objects.using(database).filter(course_id=course_id).delete()
    for index, (mode, ratio) in enumerate(ENROLLMENT_MODE_RATIOS.items()):
        count = int(ratio * daily_total)
        pass_rate = min(random.normalvariate(.45 + (.1 * index), .15), 1.0)
        cumulative_count = count + random.randint(0, 100)
        models.CourseMetaSummaryEnrollment.objects.using(database).create(
            course_id=course_id, catalog_course_title='Demo Course', catalog_course='Demo_Course',
            start_time=timezone.now() - datetime.timedelta(weeks=6),
            end_time=timezone.now() + datetime.timedelta(weeks=10),
            pacing_type='self_paced', availability='Starting Soon', enrollment_mode=mode, count=count,
            cumulative_count=cumulative_count, count_change_7_days=random.randint(-50, 50),
            passing_users=int(cumulative_count * pass_rate))

    progress.update(1)
    progress.close()
    logger.info("Done generating daily enrollment data")


def generate_weekly_data(course_id, start_date, end_date, database, delete_data=True):
    activity_types = ['PLAYED_VIDEO', 'ATTEMPTED_PROBLEM', 'POSTED_FORUM']

    # Ensure we start on a Wednesday 00:00
    days_ahead = -start_date.weekday() + 2
    start = (start_date + datetime.timedelta(days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)

    if delete_data:
        models.CourseActivityWeekly.objects.using(database).all().delete()
        logger.info("Deleted all weekly course activity.")

    logger.info("Generating new weekly course activity data...")

    progress = tqdm(total=math.ceil((end_date - start).days / 7.0))
    while start < end_date:
        active_students = random.randint(100, 4000)
        # End date should occur on Wednesday at 00:00:00
        end = start + datetime.timedelta(weeks=1)

        counts = _constrained_sum_sample_pos(len(activity_types), active_students)

        for activity_type, count in zip(activity_types, counts):
            models.CourseActivityWeekly.objects.using(database).create(
                course_id=course_id, activity_type=activity_type,
                count=count, interval_start=start, interval_end=end)

        models.CourseActivityWeekly.objects.using(database).create(course_id=course_id, activity_type='ACTIVE',
                                                                   count=active_students,
                                                                   interval_start=start, interval_end=end)

        progress.update(1)
        start = end

    progress.close()
    logger.info("Done generating weekly enrollment data")


def generate_video_timeline_data(video_id, database):
    for segment in range(100):
        active_students = random.randint(100, 4000)
        counts = _constrained_sum_sample_pos(2, active_students)
        models.VideoTimeline.objects.using(database).create(pipeline_video_id=video_id, segment=segment,
                                                            num_users=counts[0], num_views=counts[1])


def generate_video_data(course_id, video_id, module_id, database):
    users_at_start = 1234
    models.Video.objects.using(database).create(course_id=course_id, pipeline_video_id=video_id,
                                                encoded_module_id=module_id, duration=500, segment_length=5,
                                                users_at_start=users_at_start,
                                                users_at_end=random.randint(100, users_at_start))


def generate_learner_engagement_data(course_id, username, start_date, end_date, database, max_value=100):
    logger.info("Deleting learner engagement module data...")
    models.ModuleEngagement.objects.using(database).all().delete()

    logger.info("Generating learner engagement module data...")
    current = start_date
    progress = tqdm(total=(end_date - start_date).days + 1)
    while current < end_date:
        current = current + datetime.timedelta(days=1)
        for metric in engagement_events.INDIVIDUAL_EVENTS:
            num_events = random.randint(0, max_value)
            if num_events:
                for _ in range(num_events):
                    count = random.randint(0, max_value / 20)
                    entity_type = metric.split('_', 1)[0]
                    event = metric.split('_', 1)[1]
                    entity_id = f'an-id-{entity_type}-{event}'
                    models.ModuleEngagement.objects.using(database).create(
                        course_id=course_id, username=username, date=current,
                        entity_type=entity_type, entity_id=entity_id, event=event, count=count)
        progress.update(1)
    progress.close()
    logger.info("Done generating learner engagement module data")


def generate_learner_engagement_range_data(course_id, start_date, end_date, database, max_value=100):
    logger.info("Deleting engagement range data...")
    models.ModuleEngagementMetricRanges.objects.using(database).filter(course_id=course_id).delete()

    logger.info("Generating engagement range data...")
    for event in engagement_events.EVENTS:
        low_ceil = random.random() * max_value * 0.5
        models.ModuleEngagementMetricRanges.objects.using(database).create(
            course_id=course_id, start_date=start_date, end_date=end_date, metric=event,
            range_type='low', low_value=0, high_value=low_ceil)
        high_floor = random.random() * max_value * 0.5 + low_ceil
        models.ModuleEngagementMetricRanges.objects.using(database).create(
            course_id=course_id, start_date=start_date, end_date=end_date, metric=event,
            range_type='high', low_value=high_floor, high_value=max_value)


def generate_tags_distribution_data(course_id, database):
    logger.info("Deleting existed tags distribution data...")
    models.ProblemsAndTags.objects.using(database).filter(course_id=course_id).delete()

    module_id_tpl = 'i4x://test/problem/%d'
    difficulty_tag = ['Easy', 'Medium', 'Hard']
    learning_outcome_tag = ['Learned nothing', 'Learned a few things', 'Learned everything']
    problems_num = 50
    chance_difficulty = 5

    logger.info("Generating new tags distribution data...")
    for i in range(problems_num):
        module_id = module_id_tpl % i
        total_submissions = random.randint(0, 100)
        correct_submissions = random.randint(0, total_submissions)

        models.ProblemsAndTags.objects.using(database).create(
            course_id=course_id, module_id=module_id,
            tag_name='learning_outcome', tag_value=random.choice(learning_outcome_tag),
            total_submissions=total_submissions, correct_submissions=correct_submissions
        )
        if random.randint(0, chance_difficulty) != chance_difficulty:
            models.ProblemsAndTags.objects.using(database).create(
                course_id=course_id, module_id=module_id,
                tag_name='difficulty', tag_value=random.choice(difficulty_tag),
                total_submissions=total_submissions, correct_submissions=correct_submissions
            )


def fetch_videos_from_course_blocks(course_id):
    logger.info("Fetching video ids from Course Blocks API...")

    blocks_api = CourseBlocksApiClient(
        settings.BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL,
        settings.BACKEND_SERVICE_EDX_OAUTH2_KEY,
        settings.BACKEND_SERVICE_EDX_OAUTH2_SECRET,
    )
    return blocks_api.all_videos(course_id)


def generate_all_video_data(course_id, videos, database):
    logger.info("Deleting course video data...")
    models.Video.objects.using(database).all().delete()

    logger.info("Deleting video timeline data...")
    models.VideoTimeline.objects.using(database).all().delete()

    logger.info("Generating new course videos and video timeline data...")
    for video in tqdm(videos):
        generate_video_data(course_id, video['video_id'], video['video_module_id'], database)
        generate_video_timeline_data(video['video_id'], database)

    logger.info("Done generating video data")


def fake_video_ids_fallback():
    return [
        {
            'video_id': '0fac49ba',
            'video_module_id': 'i4x-edX-DemoX-video-5c90cffecd9b48b188cbfea176bf7fe9'
        }
    ]


def generate_program_data(course_ids, program_title, program_id, database):
    logger.info("Deleting existing course program data...")
    models.CourseProgramMetadata.objects.using(database).all().delete()
    program_type = 'Professional Certificate'

    for course_id in course_ids:
        models.CourseProgramMetadata.objects.using(database).create(
            course_id=course_id,
            program_title=program_title,
            program_id=program_id,
            program_type=program_type
        )
