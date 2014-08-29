# NOTE: Full URLs are used throughout these tests to ensure that the API contract is fulfilled. The URLs should *not*
# change for versions greater than 1.0.0. Tests target a specific version of the API, additional tests should be added
# for subsequent versions if there are breaking changes introduced in those versions.
import StringIO
import csv
import datetime

from django.conf import settings
from django_dynamic_fixture import G
from iso3166 import countries
import pytz

from analytics_data_api.v0 import models
from analytics_data_api.v0.serializers import ProblemResponseAnswerDistributionSerializer
from analytics_data_api.v0.tests.utils import flatten
from analyticsdataserver.tests import TestCaseWithAuthentication


# pylint: disable=no-member
class CourseViewTestCaseMixin(object):
    model = None
    api_root_path = '/api/v0/'
    path = None
    order_by = []

    def format_as_response(self, *args):
        """
        Format given data as a response that would be issued by the endpoint.

        Arguments
            args    --  Iterable list of objects
        """
        raise NotImplementedError

    def get_latest_data(self):
        """
        Return the latest row/rows that would be returned if a user made a call
        to the endpoint with no date filtering.

        Return value must be an iterable.
        """
        raise NotImplementedError

    def test_get_not_found(self):
        """ Requests made against non-existent courses should return a 404 """
        course_id = 'edX/DemoX/Non_Existent_Course'
        response = self.authenticated_get('%scourses/%s%s' % (self.api_root_path, course_id, self.path))
        self.assertEquals(response.status_code, 404)

    def test_get(self):
        """ Verify the endpoint returns an HTTP 200 status and the correct data. """
        # Validate the basic response status
        response = self.authenticated_get('%scourses/%s%s' % (self.api_root_path, self.course_id, self.path))
        self.assertEquals(response.status_code, 200)

        # Validate the data is correct and sorted chronologically
        expected = self.format_as_response(*self.get_latest_data())
        self.assertEquals(response.data, expected)

    def test_get_csv(self):
        """ Verify the endpoint returns data that has been properly converted to CSV. """
        path = '%scourses/%s%s' % (self.api_root_path, self.course_id, self.path)
        csv_content_type = 'text/csv'
        response = self.authenticated_get(path, HTTP_ACCEPT=csv_content_type)

        # Validate the basic response status and content code
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'].split(';')[0], csv_content_type)

        # Validate the actual data
        data = self.format_as_response(*self.get_latest_data())
        data = map(flatten, data)

        # The CSV renderer sorts the headers alphabetically
        fieldnames = sorted(data[0].keys())

        # Generate the expected CSV output
        expected = StringIO.StringIO()
        writer = csv.DictWriter(expected, fieldnames)
        writer.writeheader()
        writer.writerows(data)

        self.assertEqual(response.content, expected.getvalue())

    def test_get_with_intervals(self):
        """ Verify the endpoint returns multiple data points when supplied with an interval of dates. """
        raise NotImplementedError

    def assertIntervalFilteringWorks(self, expected_response, start_date, end_date):
        # If start date is after date of existing data, no data should be returned
        date = (start_date + datetime.timedelta(days=30)).strftime(settings.DATE_FORMAT)
        response = self.authenticated_get('%scourses/%s%s?start_date=%s' % (self.api_root_path, self.course_id, self.path, date))
        self.assertEquals(response.status_code, 200)
        self.assertListEqual([], response.data)

        # If end date is before date of existing data, no data should be returned
        date = (start_date - datetime.timedelta(days=30)).strftime(settings.DATE_FORMAT)
        response = self.authenticated_get('%scourses/%s%s?end_date=%s' % (self.api_root_path, self.course_id, self.path, date))
        self.assertEquals(response.status_code, 200)
        self.assertListEqual([], response.data)

        # If data falls in date range, data should be returned
        start_date = start_date.strftime(settings.DATE_FORMAT)
        end_date = end_date.strftime(settings.DATE_FORMAT)
        response = self.authenticated_get(
            '%scourses/%s%s?start_date=%s&end_date=%s' % (self.api_root_path, self.course_id, self.path, start_date, end_date))
        self.assertEquals(response.status_code, 200)
        self.assertListEqual(response.data, expected_response)


class CourseEnrollmentViewTestCaseMixin(CourseViewTestCaseMixin):
    def setUp(self):
        super(CourseEnrollmentViewTestCaseMixin, self).setUp()
        self.course_id = 'edX/DemoX/Demo_Course'
        self.date = datetime.date(2014, 1, 1)

    def get_latest_data(self):
        return self.model.objects.filter(date=self.date).order_by('date', *self.order_by)

    def test_get_with_intervals(self):
        expected = self.format_as_response(*self.model.objects.filter(date=self.date))
        self.assertIntervalFilteringWorks(expected, self.date, self.date + datetime.timedelta(days=1))


class CourseActivityLastWeekTest(TestCaseWithAuthentication):
    # pylint: disable=line-too-long
    def setUp(self):
        super(CourseActivityLastWeekTest, self).setUp()
        self.course_id = 'edX/DemoX/Demo_Course'
        interval_start = '2014-05-24T00:00:00Z'
        interval_end = '2014-06-01T00:00:00Z'
        G(models.CourseActivityByWeek, course_id=self.course_id, interval_start=interval_start,
          interval_end=interval_end,
          activity_type='POSTED_FORUM', count=100)
        G(models.CourseActivityByWeek, course_id=self.course_id, interval_start=interval_start,
          interval_end=interval_end,
          activity_type='ATTEMPTED_PROBLEM', count=200)
        G(models.CourseActivityByWeek, course_id=self.course_id, interval_start=interval_start,
          interval_end=interval_end,
          activity_type='ACTIVE', count=300)
        G(models.CourseActivityByWeek, course_id=self.course_id, interval_start=interval_start,
          interval_end=interval_end,
          activity_type='PLAYED_VIDEO', count=400)

    def test_activity(self):
        response = self.authenticated_get('/api/v0/courses/{0}/recent_activity'.format(self.course_id))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record())

    def assertValidActivityResponse(self, activity_type, count):
        response = self.authenticated_get('/api/v0/courses/{0}/recent_activity?activity_type={1}'.format(
            self.course_id, activity_type))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record(activity_type=activity_type, count=count))

    @staticmethod
    def get_activity_record(**kwargs):
        default = {
            'course_id': 'edX/DemoX/Demo_Course',
            'interval_start': datetime.datetime(2014, 5, 24, 0, 0, tzinfo=pytz.utc),
            'interval_end': datetime.datetime(2014, 6, 1, 0, 0, tzinfo=pytz.utc),
            'activity_type': 'any',
            'count': 300,
        }
        default.update(kwargs)
        default['activity_type'] = default['activity_type'].lower()
        return default

    def test_activity_auth(self):
        response = self.client.get('/api/v0/courses/{0}/recent_activity'.format(self.course_id), follow=True)
        self.assertEquals(response.status_code, 401)

    def test_url_encoded_course_id(self):
        response = self.authenticated_get('/api/v0/courses/edX%2FDemoX%2FDemo_Course/recent_activity')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record())

    def test_any_activity(self):
        self.assertValidActivityResponse('ANY', 300)
        self.assertValidActivityResponse('any', 300)

    def test_video_activity(self):
        self.assertValidActivityResponse('played_video', 400)

    def test_unknown_activity(self):
        activity_type = 'missing_activity_type'
        response = self.authenticated_get('/api/v0/courses/{0}/recent_activity?activity_type={1}'.format(
            self.course_id, activity_type))
        self.assertEquals(response.status_code, 404)

    def test_unknown_course_id(self):
        response = self.authenticated_get('/api/v0/courses/{0}/recent_activity'.format('foo'))
        self.assertEquals(response.status_code, 404)

    def test_missing_course_id(self):
        response = self.authenticated_get('/api/v0/courses/recent_activity')
        self.assertEquals(response.status_code, 404)

    def test_label_parameter(self):
        activity_type = 'played_video'
        response = self.authenticated_get('/api/v0/courses/{0}/recent_activity?label={1}'.format(
            self.course_id, activity_type))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record(activity_type=activity_type, count=400))


class CourseEnrollmentByBirthYearViewTests(CourseEnrollmentViewTestCaseMixin, TestCaseWithAuthentication):
    path = '/enrollment/birth_year'
    model = models.CourseEnrollmentByBirthYear
    order_by = ['birth_year']
    
    def setUp(self):
        super(CourseEnrollmentByBirthYearViewTests, self).setUp()
        G(self.model, course_id=self.course_id, date=self.date, birth_year=1956)
        G(self.model, course_id=self.course_id, date=self.date, birth_year=1986)
        G(self.model, course_id=self.course_id, date=self.date - datetime.timedelta(days=10), birth_year=1956)
        G(self.model, course_id=self.course_id, date=self.date - datetime.timedelta(days=10), birth_year=1986)

    def format_as_response(self, *args):
        return [
            {'course_id': str(ce.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'birth_year': ce.birth_year} for ce in args]

    def test_get(self):
        response = self.authenticated_get('/api/v0/courses/%s%s' % (self.course_id, self.path,))
        self.assertEquals(response.status_code, 200)

        expected = self.format_as_response(*self.model.objects.filter(date=self.date))
        self.assertEquals(response.data, expected)

    def test_get_with_intervals(self):
        expected = self.format_as_response(*self.model.objects.filter(date=self.date))
        self.assertIntervalFilteringWorks(expected, self.date, self.date + datetime.timedelta(days=1))


class CourseEnrollmentByEducationViewTests(CourseEnrollmentViewTestCaseMixin, TestCaseWithAuthentication):
    path = '/enrollment/education/'
    model = models.CourseEnrollmentByEducation
    order_by = ['education_level']

    def setUp(self):
        super(CourseEnrollmentByEducationViewTests, self).setUp()
        self.el1 = G(models.EducationLevel, name='Doctorate', short_name='doctorate')
        self.el2 = G(models.EducationLevel, name='Top Secret', short_name='top_secret')
        G(self.model, course_id=self.course_id, date=self.date, education_level=self.el1)
        G(self.model, course_id=self.course_id, date=self.date, education_level=self.el2)
        G(self.model, course_id=self.course_id, date=self.date - datetime.timedelta(days=2),
          education_level=self.el2)

    def format_as_response(self, *args):
        return [
            {'course_id': str(ce.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'education_level': {'name': ce.education_level.name, 'short_name': ce.education_level.short_name}} for
            ce in args]


class CourseEnrollmentByGenderViewTests(CourseEnrollmentViewTestCaseMixin, TestCaseWithAuthentication):
    path = '/enrollment/gender/'
    model = models.CourseEnrollmentByGender
    order_by = ['gender']

    def setUp(self):
        super(CourseEnrollmentByGenderViewTests, self).setUp()
        G(self.model, course_id=self.course_id, gender='m', date=self.date, count=34)
        G(self.model, course_id=self.course_id, gender='f', date=self.date, count=45)
        G(self.model, course_id=self.course_id, gender='f', date=self.date - datetime.timedelta(days=2), count=45)

    def format_as_response(self, *args):
        return [
            {'course_id': str(ce.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'gender': ce.gender} for ce in args]


# pylint: disable=no-member,no-value-for-parameter
class AnswerDistributionTests(TestCaseWithAuthentication):
    path = '/answer_distribution'
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.course_id = "org/num/run"
        cls.module_id = "i4x://org/num/run/problem/RANDOMNUMBER"
        cls.part_id1 = "i4x-org-num-run-problem-RANDOMNUMBER_2_1"
        cls.ad1 = G(
            models.ProblemResponseAnswerDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id,
            part_id=cls.part_id1
        )

    def test_get(self):
        response = self.authenticated_get('/api/v0/problems/%s%s' % (self.module_id, self.path))
        self.assertEquals(response.status_code, 200)

        expected_dict = ProblemResponseAnswerDistributionSerializer(self.ad1).data
        actual_list = response.data
        self.assertEquals(len(actual_list), 1)
        self.assertDictEqual(actual_list[0], expected_dict)

    def test_get_404(self):
        response = self.authenticated_get('/api/v0/problems/%s%s' % ("DOES-NOT-EXIST", self.path))
        self.assertEquals(response.status_code, 404)


class CourseEnrollmentViewTests(CourseEnrollmentViewTestCaseMixin, TestCaseWithAuthentication):
    model = models.CourseEnrollmentDaily
    path = '/enrollment'

    def setUp(self):
        super(CourseEnrollmentViewTests, self).setUp()
        G(self.model, course_id=self.course_id, date=self.date, count=203)
        G(self.model, course_id=self.course_id, date=self.date - datetime.timedelta(days=5), count=203)

    def format_as_response(self, *args):
        return [
            {'course_id': str(ce.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT)}
            for ce in args]


class CourseEnrollmentByLocationViewTests(CourseEnrollmentViewTestCaseMixin, TestCaseWithAuthentication):
    path = '/enrollment/location/'
    model = models.CourseEnrollmentByCountry

    def format_as_response(self, *args):
        args = [arg for arg in args if arg.country_code not in ['', 'A1', 'A2', 'AP', 'EU', 'O1', 'UNKNOWN']]
        args = sorted(args, key=lambda item: (item.date, item.course_id, item.country.alpha3))
        return [
            {'course_id': str(ce.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'country': {'alpha2': ce.country.alpha2, 'alpha3': ce.country.alpha3, 'name': ce.country.name}} for ce in
            args]

    def setUp(self):
        super(CourseEnrollmentByLocationViewTests, self).setUp()
        self.country = countries.get('US')
        G(self.model, course_id=self.course_id, country_code='US', count=455, date=self.date)
        G(self.model, course_id=self.course_id, country_code='CA', count=356, date=self.date)
        G(self.model, course_id=self.course_id, country_code='IN', count=12, date=self.date - datetime.timedelta(days=29))
        G(self.model, course_id=self.course_id, country_code='', count=356, date=self.date)
        G(self.model, course_id=self.course_id, country_code='A1', count=1, date=self.date)
        G(self.model, course_id=self.course_id, country_code='A2', count=2, date=self.date)
        G(self.model, course_id=self.course_id, country_code='AP', count=1, date=self.date)
        G(self.model, course_id=self.course_id, country_code='EU', count=4, date=self.date)
        G(self.model, course_id=self.course_id, country_code='O1', count=7, date=self.date)
