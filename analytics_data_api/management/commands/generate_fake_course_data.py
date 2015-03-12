# pylint: disable=line-too-long,invalid-name

import datetime
import logging
from optparse import make_option
import random

from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics_data_api.v0 import models


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# http://stackoverflow.com/a/3590105
def constrained_sum_sample_pos(num_values, total):
    """Return a randomly chosen list of n positive integers summing to total.
    Each such list is equally likely to occur."""

    dividers = sorted(random.sample(xrange(1, total), num_values - 1))
    return [a - b for a, b in zip(dividers + [total], [0] + dividers)]


def get_count(start):
    delta = 25 * random.gauss(0, 1)
    return int(start + delta)


class Command(BaseCommand):
    help = 'Generate fake data'
    option_list = BaseCommand.option_list + (
        make_option('-n', '--num-weeks', action='store', type="int", dest='num_weeks',
                    help='"Number of weeks worth of data to generate.'),
    )

    def generate_daily_data(self, course_id, start_date, end_date):
        # Use the preset ratios below to generate data in the specified demographics

        gender_ratios = {
            'm': 0.6107,
            'f': 0.3870,
            'o': 0.23
        }
        education_level_ratios = {
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
        country_ratios = {
            'US': 0.33,
            'GH': 0.12,
            'IN': 0.10,
            'CA': 0.14,
            'CN': 0.22,
            'DE': 0.08,
            'UNKNOWN': 0.01
        }

        enrollment_mode_ratios = {
            'audit': 0.15,
            'honor': 0.35,
            'professional': 0.10,
            'verified': 0.40
        }

        # Generate birth year ratios
        birth_years = range(1960, 2005)
        ratios = [n / 1000.0 for n in constrained_sum_sample_pos(len(birth_years), 1000)]
        birth_years = dict(zip(birth_years, ratios))

        # Delete existing data
        for model in [models.CourseEnrollmentDaily,
                      models.CourseEnrollmentModeDaily,
                      models.CourseEnrollmentByGender,
                      models.CourseEnrollmentByEducation,
                      models.CourseEnrollmentByBirthYear,
                      models.CourseEnrollmentByCountry]:
            model.objects.all().delete()

        logger.info("Deleted all daily course enrollment data.")
        logger.info("Generating new daily course enrollment data...")

        # Create new data
        daily_total = 1500
        date = start_date
        cumulative_count = 0

        while date <= end_date:
            daily_total = get_count(daily_total)
            models.CourseEnrollmentDaily.objects.create(course_id=course_id, date=date, count=daily_total)

            for mode, ratio in enrollment_mode_ratios.iteritems():
                count = int(ratio * daily_total)
                cumulative_count = max(cumulative_count + 10, count)
                models.CourseEnrollmentModeDaily.objects.create(course_id=course_id, date=date, count=count,
                                                                cumulative_count=cumulative_count, mode=mode)

            for gender, ratio in gender_ratios.iteritems():
                count = int(ratio * daily_total)
                models.CourseEnrollmentByGender.objects.create(course_id=course_id, date=date, count=count,
                                                               gender=gender)

            for education_level, ratio in education_level_ratios.iteritems():
                count = int(ratio * daily_total)
                models.CourseEnrollmentByEducation.objects.create(course_id=course_id, date=date, count=count,
                                                                  education_level=education_level)

            for country_code, ratio in country_ratios.iteritems():
                count = int(ratio * daily_total)
                models.CourseEnrollmentByCountry.objects.create(course_id=course_id, date=date, count=count,
                                                                country_code=country_code)

            for birth_year, ratio in birth_years.iteritems():
                count = int(ratio * daily_total)
                models.CourseEnrollmentByBirthYear.objects.create(course_id=course_id, date=date, count=count,
                                                                  birth_year=birth_year)

            date = date + datetime.timedelta(days=1)

        logger.info("Done!")

    def generate_weekly_data(self, course_id, start_date, end_date):
        activity_types = ['PLAYED_VIDEO', 'ATTEMPTED_PROBLEM', 'POSTED_FORUM']

        # Ensure we start on a Sunday 00:00
        days_ahead = -start_date.weekday()
        start = start_date + datetime.timedelta(days_ahead)

        models.CourseActivityWeekly.objects.all().delete()
        logger.info("Deleted all weekly course activity.")

        logger.info("Generating new weekly course activity data...")

        while start < end_date:
            active_students = random.randint(100, 4000)
            # End date should occur on Saturday at 23:59:59
            end = start + datetime.timedelta(weeks=1)

            counts = constrained_sum_sample_pos(len(activity_types), active_students)

            for activity_type, count in zip(activity_types, counts):
                models.CourseActivityWeekly.objects.create(course_id=course_id, activity_type=activity_type,
                                                           count=count, interval_start=start, interval_end=end)

            models.CourseActivityWeekly.objects.create(course_id=course_id, activity_type='ACTIVE',
                                                       count=active_students,
                                                       interval_start=start, interval_end=end)

            start = end

        logger.info("Done!")

    def generate_video_timeline_data(self, video_id):
        logger.info("Deleting video timeline data...")
        models.VideoTimeline.objects.all().delete()

        logger.info("Generating new video timeline...")
        for segment in range(100):
            active_students = random.randint(100, 4000)
            counts = constrained_sum_sample_pos(2, active_students)
            models.VideoTimeline.objects.create(pipeline_video_id=video_id, segment=segment,
                                                num_users=counts[0], num_views=counts[1])

        logger.info("Done!")

    def generate_video_data(self, course_id, video_id, module_id):
        logger.info("Deleting course video data...")
        models.Video.objects.all().delete()

        logger.info("Generating new course videos...")
        users_at_start = 1234
        models.Video.objects.create(course_id=course_id, pipeline_video_id=video_id,
                                    encoded_module_id=module_id, duration=500, segment_length=5,
                                    users_at_start=users_at_start,
                                    users_at_end=random.randint(100, users_at_start))

    def handle(self, *args, **options):
        course_id = 'edX/DemoX/Demo_Course'
        video_id = '0fac49ba'
        video_module_id = 'i4x-edX-DemoX-video-5c90cffecd9b48b188cbfea176bf7fe9'
        start_date = datetime.datetime(year=2015, month=1, day=1, tzinfo=timezone.utc)

        num_weeks = options['num_weeks']
        if num_weeks:
            end_date = start_date + datetime.timedelta(weeks=num_weeks)
        else:
            end_date = timezone.now().replace(microsecond=0)

        logger.info("Generating data for %s...", course_id)
        self.generate_weekly_data(course_id, start_date, end_date)
        self.generate_daily_data(course_id, start_date, end_date)
        self.generate_video_data(course_id, video_id, video_module_id)
        self.generate_video_timeline_data(video_id)
