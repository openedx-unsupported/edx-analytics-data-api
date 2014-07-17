import datetime
import random

from django.core.management.base import BaseCommand
from analytics_data_api.v0 import models


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
    def handle(self, *args, **options):

        days = 120
        course = models.Course.objects.first()
        start_date = datetime.date(year=2014, month=1, day=1)

        genders = {
            'm': 0.6107,
            'f': 0.3870,
            'o': 0.23
        }

        education_levels = {
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

        countries = {
            'US': 0.34,
            'GH': 0.12,
            'IN': 0.10,
            'CA': 0.14,
            'CN': 0.22,
            'DE': 0.08
        }

        birth_years = range(1960, 2005)
        ratios = [n / 1000.0 for n in constrained_sum_sample_pos(len(birth_years), 1000)]
        birth_years = dict(zip(birth_years, ratios))

        # Delete existing data
        for model in [models.CourseEnrollmentDaily, models.CourseEnrollmentByGender, models.CourseEnrollmentByEducation,
                      models.CourseEnrollmentByBirthYear, models.CourseEnrollmentByCountry]:
            model.objects.all().delete()

        # Create new data data
        daily_total = 1500
        for i in range(days):
            daily_total = get_count(daily_total)
            date = start_date + datetime.timedelta(days=i)
            models.CourseEnrollmentDaily.objects.create(course=course, date=date, count=daily_total)

            for gender, ratio in genders.iteritems():
                count = int(ratio * daily_total)
                models.CourseEnrollmentByGender.objects.create(course=course, date=date, count=count, gender=gender)

            for short_name, ratio in education_levels.iteritems():
                education_level = models.EducationLevel.objects.get(short_name=short_name)
                count = int(ratio * daily_total)
                models.CourseEnrollmentByEducation.objects.create(course=course, date=date, count=count,
                                                                  education_level=education_level)

            for code, ratio in countries.iteritems():
                country = models.Country.objects.get(code=code)
                count = int(ratio * daily_total)
                models.CourseEnrollmentByCountry.objects.create(course=course, date=date, count=count, country=country)

            for birth_year, ratio in birth_years.iteritems():
                count = int(ratio * daily_total)
                models.CourseEnrollmentByBirthYear.objects.create(course=course, date=date, count=count,
                                                                  birth_year=birth_year)
