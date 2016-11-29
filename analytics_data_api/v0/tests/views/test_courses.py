# coding=utf-8
# NOTE: Full URLs are used throughout these tests to ensure that the API contract is fulfilled. The URLs should *not*
# change for versions greater than 1.0.0. Tests target a specific version of the API, additional tests should be added
# for subsequent versions if there are breaking changes introduced in those versions.

import datetime
from itertools import groupby
import urllib

import ddt
from django.conf import settings
from django_dynamic_fixture import G
import pytz
from opaque_keys.edx.keys import CourseKey
from mock import patch, Mock

from analytics_data_api.constants import country, enrollment_modes, genders
from analytics_data_api.constants.country import get_country
from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.tests.views import CourseSamples, VerifyCsvResponseMixin
from analytics_data_api.utils import get_filename_safe_course_id
from analyticsdataserver.tests import TestCaseWithAuthentication


@ddt.ddt
class DefaultFillTestMixin(object):
    """
    Test that the view fills in missing data with a default value.
    """

    model = None

    def destroy_data(self):
        self.model.objects.all().delete()

    @ddt.data(*CourseSamples.course_ids)
    def test_default_fill(self, course_id):
        raise NotImplementedError


# pylint: disable=no-member
@ddt.ddt
class CourseViewTestCaseMixin(VerifyCsvResponseMixin):
    model = None
    api_root_path = '/api/v0/'
    path = None
    order_by = []
    csv_filename_slug = None

    def generate_data(self, course_id):
        raise NotImplementedError

    def format_as_response(self, *args):
        """
        Format given data as a response that would be issued by the endpoint.

        Arguments
            args    --  Iterable list of objects
        """
        raise NotImplementedError

    def get_latest_data(self, course_id):
        """
        Return the latest row/rows that would be returned if a user made a call
        to the endpoint with no date filtering.

        Return value must be an iterable.
        """
        raise NotImplementedError

    def csv_filename(self, course_id):
        course_key = CourseKey.from_string(course_id)
        safe_course_id = u'-'.join([course_key.org, course_key.course, course_key.run])
        return u'{0}--{1}.csv'.format(safe_course_id, self.csv_filename_slug)

    def test_get_not_found(self):
        """ Requests made against non-existent courses should return a 404 """
        course_id = u'edX/DemoX/Non_Existent_Course'
        response = self.authenticated_get(u'%scourses/%s%s' % (self.api_root_path, course_id, self.path))
        self.assertEquals(response.status_code, 404)

    def assertViewReturnsExpectedData(self, expected, course_id):
        # Validate the basic response status
        response = self.authenticated_get(u'%scourses/%s%s' % (self.api_root_path, course_id, self.path))
        self.assertEquals(response.status_code, 200)

        # Validate the data is correct and sorted chronologically
        self.assertEquals(response.data, expected)

    @ddt.data(*CourseSamples.course_ids)
    def test_get(self, course_id):
        """ Verify the endpoint returns an HTTP 200 status and the correct data. """
        self.generate_data(course_id)
        expected = self.format_as_response(*self.get_latest_data(course_id))
        self.assertViewReturnsExpectedData(expected, course_id)

    def assertCSVIsValid(self, course_id, filename):
        path = u'{0}courses/{1}{2}'.format(self.api_root_path, course_id, self.path)
        csv_content_type = 'text/csv'
        response = self.authenticated_get(path, HTTP_ACCEPT=csv_content_type)

        data = self.format_as_response(*self.get_latest_data(course_id))
        self.assertCsvResponseIsValid(response, filename, data)

    @ddt.data(*CourseSamples.course_ids)
    def test_get_csv(self, course_id):
        """ Verify the endpoint returns data that has been properly converted to CSV. """
        self.generate_data(course_id)
        self.assertCSVIsValid(course_id, self.csv_filename(course_id))

    @ddt.data(*CourseSamples.course_ids)
    def test_get_with_intervals(self, course_id):
        """ Verify the endpoint returns multiple data points when supplied with an interval of dates. """
        raise NotImplementedError

    def assertIntervalFilteringWorks(self, expected_response, course_id, start_date, end_date):
        # If start date is after date of existing data, return a 404
        date = (start_date + datetime.timedelta(days=30)).strftime(settings.DATETIME_FORMAT)
        response = self.authenticated_get(
            '%scourses/%s%s?start_date=%s' % (self.api_root_path, course_id, self.path, date))
        self.assertEquals(response.status_code, 404)

        # If end date is before date of existing data, return a 404
        date = (start_date - datetime.timedelta(days=30)).strftime(settings.DATETIME_FORMAT)
        response = self.authenticated_get(
            '%scourses/%s%s?end_date=%s' % (self.api_root_path, course_id, self.path, date))
        self.assertEquals(response.status_code, 404)

        # If data falls in date range, data should be returned
        start = start_date.strftime(settings.DATETIME_FORMAT)
        end = end_date.strftime(settings.DATETIME_FORMAT)
        response = self.authenticated_get('%scourses/%s%s?start_date=%s&end_date=%s' % (
            self.api_root_path, course_id, self.path, start, end))
        self.assertEquals(response.status_code, 200)
        self.assertListEqual(response.data, expected_response)

        # Passing dates in DATE_FORMAT still works
        start = start_date.strftime(settings.DATE_FORMAT)
        end = end_date.strftime(settings.DATE_FORMAT)
        response = self.authenticated_get('%scourses/%s%s?start_date=%s&end_date=%s' % (
            self.api_root_path, course_id, self.path, start, end))
        self.assertEquals(response.status_code, 200)
        self.assertListEqual(response.data, expected_response)


# pylint: disable=abstract-method
@ddt.ddt
class CourseEnrollmentViewTestCaseMixin(CourseViewTestCaseMixin):
    date = None

    @classmethod
    def setUpClass(cls):
        super(CourseEnrollmentViewTestCaseMixin, cls).setUpClass()
        cls.date = datetime.date(2014, 1, 1)

    def get_latest_data(self, course_id):
        return self.model.objects.filter(course_id=course_id, date=self.date).order_by('date', *self.order_by)

    @ddt.data(*CourseSamples.course_ids)
    def test_get_with_intervals(self, course_id):
        self.generate_data(course_id)
        expected = self.format_as_response(*self.model.objects.filter(date=self.date))
        self.assertIntervalFilteringWorks(expected, course_id, self.date, self.date + datetime.timedelta(days=1))


@ddt.ddt
class CourseActivityLastWeekTest(TestCaseWithAuthentication):
    def generate_data(self, course_id):
        interval_start = datetime.datetime(2014, 1, 1, tzinfo=pytz.utc)
        interval_end = interval_start + datetime.timedelta(weeks=1)
        G(models.CourseActivityWeekly, course_id=course_id, interval_start=interval_start,
          interval_end=interval_end, activity_type='POSTED_FORUM', count=100)
        G(models.CourseActivityWeekly, course_id=course_id, interval_start=interval_start,
          interval_end=interval_end,
          activity_type='ATTEMPTED_PROBLEM', count=200)
        G(models.CourseActivityWeekly, course_id=course_id, interval_start=interval_start,
          interval_end=interval_end,
          activity_type='ACTIVE', count=300)
        G(models.CourseActivityWeekly, course_id=course_id, interval_start=interval_start,
          interval_end=interval_end,
          activity_type='PLAYED_VIDEO', count=400)

    @ddt.data(*CourseSamples.course_ids)
    def test_activity(self, course_id):
        self.generate_data(course_id)
        response = self.authenticated_get(u'/api/v0/courses/{0}/recent_activity'.format(course_id))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record(course_id=course_id))

    def assertValidActivityResponse(self, course_id, activity_type, count):
        response = self.authenticated_get(u'/api/v0/courses/{0}/recent_activity?activity_type={1}'.format(
            course_id, activity_type))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record(course_id=course_id, activity_type=activity_type,
                                                                  count=count))

    @staticmethod
    def get_activity_record(**kwargs):
        datetime_format = "%Y-%m-%dT%H:%M:%SZ"
        default = {
            'course_id': kwargs['course_id'],
            'interval_start': datetime.datetime(2014, 1, 1, 0, 0, tzinfo=pytz.utc).strftime(datetime_format),
            'interval_end': datetime.datetime(2014, 1, 8, 0, 0, tzinfo=pytz.utc).strftime(datetime_format),
            'activity_type': 'any',
            'count': 300,
        }
        default.update(kwargs)
        default['activity_type'] = default['activity_type'].lower()
        return default

    @ddt.data(*CourseSamples.course_ids)
    def test_activity_auth(self, course_id):
        self.generate_data(course_id)
        response = self.client.get(u'/api/v0/courses/{0}/recent_activity'.format(course_id), follow=True)
        self.assertEquals(response.status_code, 401)

    @ddt.data(*CourseSamples.course_ids)
    def test_url_encoded_course_id(self, course_id):
        self.generate_data(course_id)
        url_encoded_course_id = urllib.quote_plus(course_id)
        response = self.authenticated_get(u'/api/v0/courses/{}/recent_activity'.format(url_encoded_course_id))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record(course_id=course_id))

    @ddt.data(*CourseSamples.course_ids)
    def test_any_activity(self, course_id):
        self.generate_data(course_id)
        self.assertValidActivityResponse(course_id, 'ANY', 300)
        self.assertValidActivityResponse(course_id, 'any', 300)

    @ddt.data(*CourseSamples.course_ids)
    def test_video_activity(self, course_id):
        self.generate_data(course_id)
        self.assertValidActivityResponse(course_id, 'played_video', 400)

    @ddt.data(*CourseSamples.course_ids)
    def test_unknown_activity(self, course_id):
        self.generate_data(course_id)
        activity_type = 'missing_activity_type'
        response = self.authenticated_get(u'/api/v0/courses/{0}/recent_activity?activity_type={1}'.format(
            course_id, activity_type))
        self.assertEquals(response.status_code, 404)

    def test_unknown_course_id(self):
        response = self.authenticated_get(u'/api/v0/courses/{0}/recent_activity'.format('foo'))
        self.assertEquals(response.status_code, 404)

    def test_missing_course_id(self):
        response = self.authenticated_get(u'/api/v0/courses/recent_activity')
        self.assertEquals(response.status_code, 404)

    @ddt.data(*CourseSamples.course_ids)
    def test_label_parameter(self, course_id):
        self.generate_data(course_id)
        activity_type = 'played_video'
        response = self.authenticated_get(u'/api/v0/courses/{0}/recent_activity?label={1}'.format(
            course_id, activity_type))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record(course_id=course_id, activity_type=activity_type,
                                                                  count=400))


@ddt.ddt
class CourseEnrollmentByBirthYearViewTests(CourseEnrollmentViewTestCaseMixin, TestCaseWithAuthentication):
    path = '/enrollment/birth_year'
    model = models.CourseEnrollmentByBirthYear
    order_by = ['birth_year']
    csv_filename_slug = u'enrollment-age'

    def generate_data(self, course_id):
        G(self.model, course_id=course_id, date=self.date, birth_year=1956)
        G(self.model, course_id=course_id, date=self.date, birth_year=1986)
        G(self.model, course_id=course_id, date=self.date - datetime.timedelta(days=10), birth_year=1956)
        G(self.model, course_id=course_id, date=self.date - datetime.timedelta(days=10), birth_year=1986)

    def format_as_response(self, *args):
        return [
            {'course_id': unicode(ce.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'birth_year': ce.birth_year, 'created': ce.created.strftime(settings.DATETIME_FORMAT)} for ce in args]

    @ddt.data(*CourseSamples.course_ids)
    def test_get(self, course_id):
        self.generate_data(course_id)
        response = self.authenticated_get('/api/v0/courses/%s%s' % (course_id, self.path,))
        self.assertEquals(response.status_code, 200)

        expected = self.format_as_response(*self.model.objects.filter(date=self.date))
        self.assertEquals(response.data, expected)


class CourseEnrollmentByEducationViewTests(CourseEnrollmentViewTestCaseMixin, TestCaseWithAuthentication):
    path = '/enrollment/education/'
    model = models.CourseEnrollmentByEducation
    order_by = ['education_level']
    csv_filename_slug = u'enrollment-education'

    def generate_data(self, course_id):
        G(self.model, course_id=course_id, date=self.date, education_level=self.el1)
        G(self.model, course_id=course_id, date=self.date, education_level=self.el2)
        G(self.model, course_id=course_id, date=self.date - datetime.timedelta(days=2), education_level=self.el2)

    @classmethod
    def setUpClass(cls):
        super(CourseEnrollmentByEducationViewTests, cls).setUpClass()
        cls.el1 = 'doctorate'
        cls.el2 = 'top_secret'

    def format_as_response(self, *args):
        return [
            {'course_id': unicode(ce.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'education_level': ce.education_level, 'created': ce.created.strftime(settings.DATETIME_FORMAT)} for
            ce in args]


@ddt.ddt
class CourseEnrollmentByGenderViewTests(CourseEnrollmentViewTestCaseMixin, DefaultFillTestMixin,
                                        TestCaseWithAuthentication):
    path = '/enrollment/gender/'
    model = models.CourseEnrollmentByGender
    order_by = ['gender']
    csv_filename_slug = u'enrollment-gender'

    def generate_data(self, course_id):
        _genders = ['f', 'm', 'o', None]
        days = 2

        for day in range(days):
            for gender in _genders:
                G(self.model,
                  course_id=course_id,
                  date=self.date - datetime.timedelta(days=day),
                  gender=gender,
                  count=100 + day)

    def tearDown(self):
        self.destroy_data()

    def serialize_enrollment(self, enrollment):
        return {
            'created': enrollment.created.strftime(settings.DATETIME_FORMAT),
            'course_id': unicode(enrollment.course_id),
            'date': enrollment.date.strftime(settings.DATE_FORMAT),
            enrollment.cleaned_gender: enrollment.count
        }

    def format_as_response(self, *args):
        response = []

        # Group by date
        for _key, group in groupby(args, lambda x: x.date):
            # Iterate over groups and create a single item with genders
            item = {}

            for enrollment in group:
                item.update(self.serialize_enrollment(enrollment))

            response.append(item)

        return response

    @ddt.data(*CourseSamples.course_ids)
    def test_default_fill(self, course_id):
        # Create a single entry for a single gender
        enrollment = G(self.model, course_id=course_id, date=self.date, gender='f', count=1)

        # Create the expected data
        _genders = list(genders.ALL)
        _genders.remove(genders.FEMALE)

        expected = self.serialize_enrollment(enrollment)

        for gender in _genders:
            expected[gender] = 0

        self.assertViewReturnsExpectedData([expected], course_id)


class CourseEnrollmentViewTests(CourseEnrollmentViewTestCaseMixin, TestCaseWithAuthentication):
    model = models.CourseEnrollmentDaily
    path = '/enrollment'
    csv_filename_slug = u'enrollment'

    def generate_data(self, course_id):
        G(self.model, course_id=course_id, date=self.date, count=203)
        G(self.model, course_id=course_id, date=self.date - datetime.timedelta(days=5), count=203)

    def format_as_response(self, *args):
        return [
            {'course_id': unicode(ce.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'created': ce.created.strftime(settings.DATETIME_FORMAT)}
            for ce in args]


@ddt.ddt
class CourseEnrollmentModeViewTests(CourseEnrollmentViewTestCaseMixin, DefaultFillTestMixin,
                                    TestCaseWithAuthentication):
    model = models.CourseEnrollmentModeDaily
    path = '/enrollment/mode'
    csv_filename_slug = u'enrollment_mode'

    def generate_data(self, course_id):
        for mode in enrollment_modes.ALL:
            G(self.model, course_id=course_id, date=self.date, mode=mode)

    def serialize_enrollment(self, enrollment):
        return {
            u'course_id': enrollment.course_id,
            u'date': enrollment.date.strftime(settings.DATE_FORMAT),
            u'created': enrollment.created.strftime(settings.DATETIME_FORMAT),
            enrollment.mode: enrollment.count
        }

    def format_as_response(self, *args):
        arg = args[0]
        response = self.serialize_enrollment(arg)
        total = 0
        cumulative = 0

        for ce in args:
            total += ce.count
            cumulative += ce.cumulative_count
            response[ce.mode] = ce.count

        response[enrollment_modes.PROFESSIONAL] += response[enrollment_modes.PROFESSIONAL_NO_ID]
        del response[enrollment_modes.PROFESSIONAL_NO_ID]

        response[u'count'] = total
        response[u'cumulative_count'] = cumulative

        return [response]

    @ddt.data(*CourseSamples.course_ids)
    def test_default_fill(self, course_id):
        self.destroy_data()

        # Create a single entry for a single enrollment mode
        enrollment = G(self.model, course_id=course_id, date=self.date, mode=enrollment_modes.AUDIT,
                       count=1, cumulative_count=100)

        # Create the expected data
        modes = list(enrollment_modes.ALL)
        modes.remove(enrollment_modes.PROFESSIONAL_NO_ID)

        expected = {}
        for mode in modes:
            expected[mode] = 0

        expected.update(self.serialize_enrollment(enrollment))
        expected[u'count'] = 1
        expected[u'cumulative_count'] = 100

        self.assertViewReturnsExpectedData([expected], course_id)


class CourseEnrollmentByLocationViewTests(CourseEnrollmentViewTestCaseMixin, TestCaseWithAuthentication):
    path = '/enrollment/location/'
    model = models.CourseEnrollmentByCountry
    csv_filename_slug = u'enrollment-location'

    def format_as_response(self, *args):
        unknown = {'course_id': None, 'count': 0, 'date': None,
                   'country': {'alpha2': None, 'alpha3': None, 'name': country.UNKNOWN_COUNTRY_CODE}}

        for arg in args:
            if arg.country.name == country.UNKNOWN_COUNTRY_CODE:
                unknown['course_id'] = arg.course_id
                unknown['date'] = arg.date.strftime(settings.DATE_FORMAT)
                unknown['count'] += arg.count
                unknown['created'] = arg.created.strftime(settings.DATETIME_FORMAT)

        args = [arg for arg in args if arg.country != country.UNKNOWN_COUNTRY]
        args = sorted(args, key=lambda item: (item.date, item.course_id, item.country.alpha3))

        response = [unknown]
        response += [
            {'course_id': unicode(ce.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'country': {'alpha2': ce.country.alpha2, 'alpha3': ce.country.alpha3, 'name': ce.country.name},
             'created': ce.created.strftime(settings.DATETIME_FORMAT)} for ce in
            args]

        return response

    def generate_data(self, course_id):
        G(self.model, course_id=course_id, country_code='US', count=455, date=self.date)
        G(self.model, course_id=course_id, country_code='CA', count=356, date=self.date)
        G(self.model, course_id=course_id, country_code='IN', count=12, date=self.date - datetime.timedelta(days=29))
        G(self.model, course_id=course_id, country_code='', count=356, date=self.date)
        G(self.model, course_id=course_id, country_code='A1', count=1, date=self.date)
        G(self.model, course_id=course_id, country_code='A2', count=2, date=self.date)
        G(self.model, course_id=course_id, country_code='AP', count=1, date=self.date)
        G(self.model, course_id=course_id, country_code='EU', count=4, date=self.date)
        G(self.model, course_id=course_id, country_code='O1', count=7, date=self.date)

    @classmethod
    def setUpClass(cls):
        super(CourseEnrollmentByLocationViewTests, cls).setUpClass()
        cls.country = get_country('US')


@ddt.ddt
class CourseActivityWeeklyViewTests(CourseViewTestCaseMixin, TestCaseWithAuthentication):
    path = '/activity/'
    default_order_by = 'interval_end'
    model = models.CourseActivityWeekly
    # activity_types = ['ACTIVE', 'ATTEMPTED_PROBLEM', 'PLAYED_VIDEO', 'POSTED_FORUM']
    activity_types = ['ACTIVE', 'ATTEMPTED_PROBLEM', 'PLAYED_VIDEO']
    csv_filename_slug = u'engagement-activity'

    def generate_data(self, course_id):
        for activity_type in self.activity_types:
            G(models.CourseActivityWeekly,
              course_id=course_id,
              interval_start=self.interval_start,
              interval_end=self.interval_end,
              activity_type=activity_type,
              count=100)

    @classmethod
    def setUpClass(cls):
        super(CourseActivityWeeklyViewTests, cls).setUpClass()
        cls.interval_start = datetime.datetime(2014, 1, 1, tzinfo=pytz.utc)
        cls.interval_end = cls.interval_start + datetime.timedelta(weeks=1)

    def get_latest_data(self, course_id):
        return self.model.objects.filter(course_id=course_id, interval_end=self.interval_end)

    def format_as_response(self, *args):
        response = []

        # Group by date
        for _key, group in groupby(args, lambda x: x.interval_end):
            # Iterate over groups and create a single item with all activity types
            item = {}

            for activity in group:
                activity_type = activity.activity_type.lower()
                if activity_type == 'active':
                    activity_type = 'any'

                item.update({
                    u'course_id': activity.course_id,
                    u'interval_start': activity.interval_start.strftime(settings.DATETIME_FORMAT),
                    u'interval_end': activity.interval_end.strftime(settings.DATETIME_FORMAT),
                    u'created': activity.created.strftime(settings.DATETIME_FORMAT),
                    activity_type: activity.count
                })

            response.append(item)

        return response

    @ddt.data(*CourseSamples.course_ids)
    def test_get_with_intervals(self, course_id):
        """ Verify the endpoint returns multiple data points when supplied with an interval of dates. """
        self.generate_data(course_id)
        interval_start = self.interval_start + datetime.timedelta(weeks=1)
        interval_end = self.interval_end + datetime.timedelta(weeks=1)

        for activity_type in self.activity_types:
            G(models.CourseActivityWeekly,
              course_id=course_id,
              interval_start=interval_start,
              interval_end=interval_end,
              activity_type=activity_type,
              count=200)

        expected = self.format_as_response(*self.model.objects.all())
        self.assertEqual(len(expected), 2)
        self.assertIntervalFilteringWorks(expected, course_id, self.interval_start,
                                          interval_end + datetime.timedelta(days=1))


@ddt.ddt
class CourseProblemsListViewTests(TestCaseWithAuthentication):
    def _get_data(self, course_id):
        """
        Retrieve data for the specified course.
        """
        url = '/api/v0/courses/{}/problems/'.format(course_id)
        return self.authenticated_get(url)

    @ddt.data(*CourseSamples.course_ids)
    def test_get(self, course_id):
        """
        The view should return data when data exists for the course.
        """

        # This data should never be returned by the tests below because the course_id doesn't match.
        G(models.ProblemFirstLastResponseAnswerDistribution)

        # Create multiple objects here to test the grouping. Add a model with a different module_id to break up the
        # natural order and ensure the view properly sorts the objects before grouping.
        module_id = u'i4x://test/problem/1'
        alt_module_id = u'i4x://test/problem/2'
        created = datetime.datetime.utcnow()
        alt_created = created + datetime.timedelta(seconds=2)
        date_time_format = '%Y-%m-%d %H:%M:%S'

        o1 = G(models.ProblemFirstLastResponseAnswerDistribution, course_id=course_id, module_id=module_id,
               correct=True, last_response_count=100, created=created.strftime(date_time_format))
        o2 = G(models.ProblemFirstLastResponseAnswerDistribution, course_id=course_id, module_id=alt_module_id,
               correct=True, last_response_count=100, created=created.strftime(date_time_format))
        o3 = G(models.ProblemFirstLastResponseAnswerDistribution, course_id=course_id, module_id=module_id,
               correct=False, last_response_count=200, created=alt_created.strftime(date_time_format))

        expected = [
            {
                'module_id': module_id,
                'total_submissions': 150,
                'correct_submissions': 50,
                'part_ids': [unicode(o1.part_id), unicode(o3.part_id)],
                'created': alt_created.strftime(settings.DATETIME_FORMAT)
            },
            {
                'module_id': alt_module_id,
                'total_submissions': 100,
                'correct_submissions': 100,
                'part_ids': [unicode(o2.part_id)],
                'created': unicode(created.strftime(settings.DATETIME_FORMAT))
            }
        ]

        response = self._get_data(course_id)
        self.assertEquals(response.status_code, 200)
        self.assertListEqual([dict(d) for d in response.data], expected)

    def test_get_404(self):
        """
        The view should return 404 if no data exists for the course.
        """

        response = self._get_data('foo/bar/course')
        self.assertEquals(response.status_code, 404)


@ddt.ddt
class CourseProblemsAndTagsListViewTests(TestCaseWithAuthentication):
    def _get_data(self, course_id):
        """
        Retrieve data for the specified course.
        """
        url = '/api/v0/courses/{}/problems_and_tags/'.format(course_id)
        return self.authenticated_get(url)

    @ddt.data(*CourseSamples.course_ids)
    def test_get(self, course_id):
        """
        The view should return data when data exists for the course.
        """

        # This data should never be returned by the tests below because the course_id doesn't match.
        G(models.ProblemsAndTags)

        # Create multiple objects here to test the grouping. Add a model with a different module_id to break up the
        # natural order and ensure the view properly sorts the objects before grouping.
        module_id = u'i4x://test/problem/1'
        alt_module_id = u'i4x://test/problem/2'

        tags = {
            'difficulty': ['Easy', 'Medium', 'Hard'],
            'learning_outcome': ['Learned nothing', 'Learned a few things', 'Learned everything']
        }

        created = datetime.datetime.utcnow()
        alt_created = created + datetime.timedelta(seconds=2)

        G(models.ProblemsAndTags, course_id=course_id, module_id=module_id,
          tag_name='difficulty', tag_value=tags['difficulty'][0],
          total_submissions=11, correct_submissions=4, created=created)
        G(models.ProblemsAndTags, course_id=course_id, module_id=module_id,
          tag_name='learning_outcome', tag_value=tags['learning_outcome'][1],
          total_submissions=11, correct_submissions=4, created=alt_created)
        G(models.ProblemsAndTags, course_id=course_id, module_id=alt_module_id,
          tag_name='learning_outcome', tag_value=tags['learning_outcome'][2],
          total_submissions=4, correct_submissions=0, created=created)

        expected = [
            {
                'module_id': module_id,
                'total_submissions': 11,
                'correct_submissions': 4,
                'tags': {
                    u'difficulty': u'Easy',
                    u'learning_outcome': u'Learned a few things',
                },
                'created': alt_created.strftime(settings.DATETIME_FORMAT)
            },
            {
                'module_id': alt_module_id,
                'total_submissions': 4,
                'correct_submissions': 0,
                'tags': {
                    u'learning_outcome': u'Learned everything',
                },
                'created': created.strftime(settings.DATETIME_FORMAT)
            }
        ]

        response = self._get_data(course_id)
        self.assertEquals(response.status_code, 200)
        self.assertListEqual(sorted([dict(d) for d in response.data]), sorted(expected))

    def test_get_404(self):
        """
        The view should return 404 if no data exists for the course.
        """

        response = self._get_data('foo/bar/course')
        self.assertEquals(response.status_code, 404)


@ddt.ddt
class CourseVideosListViewTests(TestCaseWithAuthentication):
    def _get_data(self, course_id):
        """
        Retrieve videos for a specified course.
        """
        url = '/api/v0/courses/{}/videos/'.format(course_id)
        return self.authenticated_get(url)

    @ddt.data(*CourseSamples.course_ids)
    def test_get(self, course_id):
        # add a blank row, which shouldn't be included in results
        G(models.Video)

        module_id = 'i4x-test-video-1'
        video_id = 'v1d30'
        created = datetime.datetime.utcnow()
        date_time_format = '%Y-%m-%d %H:%M:%S'
        G(models.Video, course_id=course_id, encoded_module_id=module_id,
          pipeline_video_id=video_id, duration=100, segment_length=1, users_at_start=50, users_at_end=10,
          created=created.strftime(date_time_format))

        alt_module_id = 'i4x-test-video-2'
        alt_video_id = 'a1d30'
        alt_created = created + datetime.timedelta(seconds=10)
        G(models.Video, course_id=course_id, encoded_module_id=alt_module_id,
          pipeline_video_id=alt_video_id, duration=200, segment_length=5, users_at_start=1050, users_at_end=50,
          created=alt_created.strftime(date_time_format))

        expected = [
            {
                'duration': 100,
                'encoded_module_id': module_id,
                'pipeline_video_id': video_id,
                'segment_length': 1,
                'users_at_start': 50,
                'users_at_end': 10,
                'created': created.strftime(settings.DATETIME_FORMAT)
            },
            {
                'duration': 200,
                'encoded_module_id': alt_module_id,
                'pipeline_video_id': alt_video_id,
                'segment_length': 5,
                'users_at_start': 1050,
                'users_at_end': 50,
                'created': alt_created.strftime(settings.DATETIME_FORMAT)
            }
        ]

        response = self._get_data(course_id)
        self.assertEquals(response.status_code, 200)
        self.assertListEqual(response.data, expected)

    def test_get_404(self):
        response = self._get_data('foo/bar/course')
        self.assertEquals(response.status_code, 404)


@ddt.ddt
class CourseReportDownloadViewTests(TestCaseWithAuthentication):

    path = '/api/v0/courses/{course_id}/reports/{report_name}'

    @patch('django.core.files.storage.default_storage.exists', Mock(return_value=False))
    @ddt.data(*CourseSamples.course_ids)
    def test_report_file_not_found(self, course_id):
        response = self.authenticated_get(
            self.path.format(
                course_id=course_id,
                report_name='problem_response'
            )
        )
        self.assertEqual(response.status_code, 404)

    @ddt.data(*CourseSamples.course_ids)
    def test_report_not_supported(self, course_id):
        response = self.authenticated_get(
            self.path.format(
                course_id=course_id,
                report_name='fake_problem_that_we_dont_support'
            )
        )
        self.assertEqual(response.status_code, 404)

    @patch('analytics_data_api.utils.default_storage', object())
    @ddt.data(*CourseSamples.course_ids)
    def test_incompatible_storage_provider(self, course_id):
        response = self.authenticated_get(
            self.path.format(
                course_id=course_id,
                report_name='problem_response'
            )
        )
        self.assertEqual(response.status_code, 501)

    @patch('django.core.files.storage.default_storage.exists', Mock(return_value=True))
    @patch('django.core.files.storage.default_storage.url', Mock(return_value='http://fake'))
    @patch(
        'django.core.files.storage.default_storage.modified_time',
        Mock(return_value=datetime.datetime(2014, 1, 1, tzinfo=pytz.utc))
    )
    @patch('django.core.files.storage.default_storage.size', Mock(return_value=1000))
    @patch(
        'analytics_data_api.utils.get_expiration_date',
        Mock(return_value=datetime.datetime(2014, 1, 1, tzinfo=pytz.utc))
    )
    @ddt.data(*CourseSamples.course_ids)
    def test_make_working_link(self, course_id):
        response = self.authenticated_get(
            self.path.format(
                course_id=course_id,
                report_name='problem_response'
            )
        )
        self.assertEqual(response.status_code, 200)
        expected = {
            'course_id': get_filename_safe_course_id(course_id),
            'report_name': 'problem_response',
            'download_url': 'http://fake',
            'last_modified': datetime.datetime(2014, 1, 1, tzinfo=pytz.utc).strftime(settings.DATETIME_FORMAT),
            'expiration_date': datetime.datetime(2014, 1, 1, tzinfo=pytz.utc).strftime(settings.DATETIME_FORMAT),
            'file_size': 1000
        }
        self.assertEqual(response.data, expected)

    @patch('django.core.files.storage.default_storage.exists', Mock(return_value=True))
    @patch('django.core.files.storage.default_storage.url', Mock(return_value='http://fake'))
    @patch(
        'django.core.files.storage.default_storage.modified_time',
        Mock(return_value=datetime.datetime(2014, 1, 1, tzinfo=pytz.utc))
    )
    @patch('django.core.files.storage.default_storage.size', Mock(side_effect=NotImplementedError()))
    @patch(
        'analytics_data_api.utils.get_expiration_date',
        Mock(return_value=datetime.datetime(2014, 1, 1, tzinfo=pytz.utc))
    )
    @ddt.data(*CourseSamples.course_ids)
    def test_make_working_link_with_missing_size(self, course_id):
        response = self.authenticated_get(
            self.path.format(
                course_id=course_id,
                report_name='problem_response'
            )
        )
        self.assertEqual(response.status_code, 200)
        expected = {
            'course_id': get_filename_safe_course_id(course_id),
            'report_name': 'problem_response',
            'download_url': 'http://fake',
            'last_modified': datetime.datetime(2014, 1, 1, tzinfo=pytz.utc).strftime(settings.DATETIME_FORMAT),
            'expiration_date': datetime.datetime(2014, 1, 1, tzinfo=pytz.utc).strftime(settings.DATETIME_FORMAT)
        }
        self.assertEqual(response.data, expected)

    @patch('django.core.files.storage.default_storage.exists', Mock(return_value=True))
    @patch('django.core.files.storage.default_storage.url', Mock(return_value='http://fake'))
    @patch('django.core.files.storage.default_storage.modified_time', Mock(side_effect=NotImplementedError()))
    @patch('django.core.files.storage.default_storage.size', Mock(return_value=1000))
    @patch(
        'analytics_data_api.utils.get_expiration_date',
        Mock(return_value=datetime.datetime(2014, 1, 1, tzinfo=pytz.utc))
    )
    @ddt.data(*CourseSamples.course_ids)
    def test_make_working_link_with_missing_last_modified_date(self, course_id):
        response = self.authenticated_get(
            self.path.format(
                course_id=course_id,
                report_name='problem_response'
            )
        )
        self.assertEqual(response.status_code, 200)
        expected = {
            'course_id': get_filename_safe_course_id(course_id),
            'report_name': 'problem_response',
            'download_url': 'http://fake',
            'file_size': 1000,
            'expiration_date': datetime.datetime(2014, 1, 1, tzinfo=pytz.utc).strftime(settings.DATETIME_FORMAT)
        }
        self.assertEqual(response.data, expected)


class CourseSummariesViewTests(TestCaseWithAuthentication):
    model = models.CourseMetaSummaryEnrollment
    serializer = serializers.CourseMetaSummaryEnrollmentSerializer
    path = '/course_summaries'
    expected_summaries = []
    fake_course_ids = ['edX/DemoX/Demo_Course', 'edX/DemoX/2', 'edX/DemoX/3', 'edX/DemoX/4']
    #  csv_filename_slug = u'course_summaries'

    def setUp(self):
        super(CourseSummariesViewTests, self).setUp()
        self.generate_data()

    def generate_data(self):
        for course_id in self.fake_course_ids:
            self.expected_summaries.append(self.serializer(
                G(self.model, course_id=course_id, count=10, cumulative_count=15)).data)

    def test_get(self):
        response = self.authenticated_get(u'/api/v0/course_summaries/?course_ids=%s' % ','.join(self.fake_course_ids))
        self.assertEquals(response.status_code, 200)
        self.assertItemsEqual(response.data, self.expected_summaries)

    def test_no_summaries(self):
        self.model.objects.all().delete()
        response = self.authenticated_get(u'/api/v0/course_summaries/?course_ids=%s' % ','.join(self.fake_course_ids))
        self.assertEquals(response.status_code, 404)
