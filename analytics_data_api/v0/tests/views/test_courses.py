# coding=utf-8
# NOTE: Full URLs are used throughout these tests to ensure that the API contract is fulfilled. The URLs should *not*
# change for versions greater than 1.0.0. Tests target a specific version of the API, additional tests should be added
# for subsequent versions if there are breaking changes introduced in those versions.

import StringIO
import csv
import datetime
from itertools import groupby
import urllib

from django.conf import settings
from django_dynamic_fixture import G
from django.utils import timezone
import pytz

from analytics_data_api.constants.country import get_country
from analytics_data_api.v0 import models
from analytics_data_api.constants import country, enrollment_modes, genders
from analytics_data_api.v0.models import CourseActivityWeekly
from analytics_data_api.v0.tests.utils import flatten
from analytics_data_api.v0.tests.views import DemoCourseMixin, DEMO_COURSE_ID
from analyticsdataserver.tests import TestCaseWithAuthentication


class DefaultFillTestMixin(object):
    """
    Test that the view fills in missing data with a default value.
    """

    model = None

    def destroy_data(self):
        self.model.objects.all().delete()

    def test_default_fill(self):
        raise NotImplementedError


# pylint: disable=no-member
class CourseViewTestCaseMixin(DemoCourseMixin):
    model = None
    api_root_path = '/api/v0/'
    path = None
    order_by = []
    csv_filename_slug = None

    def generate_data(self, course_id=None):
        raise NotImplementedError

    def format_as_response(self, *args):
        """
        Format given data as a response that would be issued by the endpoint.

        Arguments
            args    --  Iterable list of objects
        """
        raise NotImplementedError

    def get_latest_data(self, course_id=None):
        """
        Return the latest row/rows that would be returned if a user made a call
        to the endpoint with no date filtering.

        Return value must be an iterable.
        """
        raise NotImplementedError

    def get_csv_filename(self):
        return u'edX-DemoX-Demo_2014--{0}.csv'.format(self.csv_filename_slug)

    def test_get_not_found(self):
        """ Requests made against non-existent courses should return a 404 """
        course_id = u'edX/DemoX/Non_Existent_Course'
        response = self.authenticated_get(u'%scourses/%s%s' % (self.api_root_path, course_id, self.path))
        self.assertEquals(response.status_code, 404)

    def assertViewReturnsExpectedData(self, expected):
        # Validate the basic response status
        response = self.authenticated_get(u'%scourses/%s%s' % (self.api_root_path, self.course_id, self.path))
        self.assertEquals(response.status_code, 200)

        # Validate the data is correct and sorted chronologically
        self.assertEquals(response.data, expected)

    def test_get(self):
        """ Verify the endpoint returns an HTTP 200 status and the correct data. """
        expected = self.format_as_response(*self.get_latest_data())
        self.assertViewReturnsExpectedData(expected)

    def assertCSVIsValid(self, course_id, filename):
        path = u'{0}courses/{1}{2}'.format(self.api_root_path, course_id, self.path)
        csv_content_type = 'text/csv'
        response = self.authenticated_get(path, HTTP_ACCEPT=csv_content_type)

        # Validate the basic response status, content type, and filename
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'].split(';')[0], csv_content_type)
        self.assertEquals(response['Content-Disposition'], u'attachment; filename={}'.format(filename))

        # Validate the actual data
        data = self.format_as_response(*self.get_latest_data(course_id=course_id))
        data = map(flatten, data)

        # The CSV renderer sorts the headers alphabetically
        fieldnames = sorted(data[0].keys())

        # Generate the expected CSV output
        expected = StringIO.StringIO()
        writer = csv.DictWriter(expected, fieldnames)
        writer.writeheader()
        writer.writerows(data)
        self.assertEqual(response.content, expected.getvalue())

    def test_get_csv(self):
        """ Verify the endpoint returns data that has been properly converted to CSV. """
        self.assertCSVIsValid(self.course_id, self.get_csv_filename())

    def test_get_csv_with_deprecated_key(self):
        """
        Verify the endpoint returns data that has been properly converted to CSV even if the course ID is deprecated.
        """
        course_id = u'edX/DemoX/Demo_Course'
        self.generate_data(course_id)
        filename = u'{0}--{1}.csv'.format(u'edX-DemoX-Demo_Course', self.csv_filename_slug)
        self.assertCSVIsValid(course_id, filename)

    def test_get_with_intervals(self):
        """ Verify the endpoint returns multiple data points when supplied with an interval of dates. """
        raise NotImplementedError

    def assertIntervalFilteringWorks(self, expected_response, start_date, end_date):
        # If start date is after date of existing data, return a 404
        date = (start_date + datetime.timedelta(days=30)).strftime(settings.DATE_FORMAT)
        response = self.authenticated_get(
            '%scourses/%s%s?start_date=%s' % (self.api_root_path, self.course_id, self.path, date))
        self.assertEquals(response.status_code, 404)

        # If end date is before date of existing data, return a 404
        date = (start_date - datetime.timedelta(days=30)).strftime(settings.DATE_FORMAT)
        response = self.authenticated_get(
            '%scourses/%s%s?end_date=%s' % (self.api_root_path, self.course_id, self.path, date))
        self.assertEquals(response.status_code, 404)

        # If data falls in date range, data should be returned
        start_date = start_date.strftime(settings.DATE_FORMAT)
        end_date = end_date.strftime(settings.DATE_FORMAT)
        response = self.authenticated_get('%scourses/%s%s?start_date=%s&end_date=%s' % (
            self.api_root_path, self.course_id, self.path, start_date, end_date))
        self.assertEquals(response.status_code, 200)
        self.assertListEqual(response.data, expected_response)


# pylint: disable=abstract-method
class CourseEnrollmentViewTestCaseMixin(CourseViewTestCaseMixin):
    date = None

    def setUp(self):
        super(CourseEnrollmentViewTestCaseMixin, self).setUp()
        self.date = datetime.date(2014, 1, 1)

    def get_latest_data(self, course_id=None):
        course_id = course_id or self.course_id
        return self.model.objects.filter(course_id=course_id, date=self.date).order_by('date', *self.order_by)

    def test_get_with_intervals(self):
        expected = self.format_as_response(*self.model.objects.filter(date=self.date))
        self.assertIntervalFilteringWorks(expected, self.date, self.date + datetime.timedelta(days=1))


class CourseActivityLastWeekTest(DemoCourseMixin, TestCaseWithAuthentication):
    def generate_data(self, course_id=None):
        course_id = course_id or self.course_id
        interval_start = datetime.datetime(2014, 1, 1, tzinfo=pytz.utc)
        interval_end = interval_start + datetime.timedelta(weeks=1)
        # G(models.CourseActivityWeekly, course_id=course_id, interval_start=interval_start,
        # interval_end=interval_end,
        # activity_type='POSTED_FORUM', count=100)
        G(models.CourseActivityWeekly, course_id=course_id, interval_start=interval_start,
          interval_end=interval_end,
          activity_type='ATTEMPTED_PROBLEM', count=200)
        G(models.CourseActivityWeekly, course_id=course_id, interval_start=interval_start,
          interval_end=interval_end,
          activity_type='ACTIVE', count=300)
        G(models.CourseActivityWeekly, course_id=course_id, interval_start=interval_start,
          interval_end=interval_end,
          activity_type='PLAYED_VIDEO', count=400)

    def setUp(self):
        super(CourseActivityLastWeekTest, self).setUp()
        self.generate_data()

    def test_activity(self):
        response = self.authenticated_get(u'/api/v0/courses/{0}/recent_activity'.format(self.course_id))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record())

    def assertValidActivityResponse(self, activity_type, count):
        response = self.authenticated_get(u'/api/v0/courses/{0}/recent_activity?activity_type={1}'.format(
            self.course_id, activity_type))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record(activity_type=activity_type, count=count))

    @staticmethod
    def get_activity_record(**kwargs):
        default = {
            'course_id': DEMO_COURSE_ID,
            'interval_start': datetime.datetime(2014, 1, 1, 0, 0, tzinfo=pytz.utc),
            'interval_end': datetime.datetime(2014, 1, 8, 0, 0, tzinfo=pytz.utc),
            'activity_type': 'any',
            'count': 300,
        }
        default.update(kwargs)
        default['activity_type'] = default['activity_type'].lower()
        return default

    def test_activity_auth(self):
        response = self.client.get(u'/api/v0/courses/{0}/recent_activity'.format(self.course_id), follow=True)
        self.assertEquals(response.status_code, 401)

    def test_url_encoded_course_id(self):
        url_encoded_course_id = urllib.quote_plus(self.course_id)
        response = self.authenticated_get(u'/api/v0/courses/{}/recent_activity'.format(url_encoded_course_id))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record())

    def test_any_activity(self):
        self.assertValidActivityResponse('ANY', 300)
        self.assertValidActivityResponse('any', 300)

    def test_video_activity(self):
        self.assertValidActivityResponse('played_video', 400)

    def test_unknown_activity(self):
        activity_type = 'missing_activity_type'
        response = self.authenticated_get(u'/api/v0/courses/{0}/recent_activity?activity_type={1}'.format(
            self.course_id, activity_type))
        self.assertEquals(response.status_code, 404)

    def test_unknown_course_id(self):
        response = self.authenticated_get(u'/api/v0/courses/{0}/recent_activity'.format('foo'))
        self.assertEquals(response.status_code, 404)

    def test_missing_course_id(self):
        response = self.authenticated_get(u'/api/v0/courses/recent_activity')
        self.assertEquals(response.status_code, 404)

    def test_label_parameter(self):
        activity_type = 'played_video'
        response = self.authenticated_get(u'/api/v0/courses/{0}/recent_activity?label={1}'.format(
            self.course_id, activity_type))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data, self.get_activity_record(activity_type=activity_type, count=400))


class CourseEnrollmentByBirthYearViewTests(CourseEnrollmentViewTestCaseMixin, TestCaseWithAuthentication):
    path = '/enrollment/birth_year'
    model = models.CourseEnrollmentByBirthYear
    order_by = ['birth_year']
    csv_filename_slug = u'enrollment-age'

    def generate_data(self, course_id=None):
        course_id = course_id or self.course_id
        G(self.model, course_id=course_id, date=self.date, birth_year=1956)
        G(self.model, course_id=course_id, date=self.date, birth_year=1986)
        G(self.model, course_id=course_id, date=self.date - datetime.timedelta(days=10), birth_year=1956)
        G(self.model, course_id=course_id, date=self.date - datetime.timedelta(days=10), birth_year=1986)

    def setUp(self):
        super(CourseEnrollmentByBirthYearViewTests, self).setUp()
        self.generate_data()

    def format_as_response(self, *args):
        return [
            {'course_id': unicode(ce.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'birth_year': ce.birth_year, 'created': ce.created.strftime(settings.DATETIME_FORMAT)} for ce in args]

    def test_get(self):
        response = self.authenticated_get('/api/v0/courses/%s%s' % (self.course_id, self.path,))
        self.assertEquals(response.status_code, 200)

        expected = self.format_as_response(*self.model.objects.filter(date=self.date))
        self.assertEquals(response.data, expected)


class CourseEnrollmentByEducationViewTests(CourseEnrollmentViewTestCaseMixin, TestCaseWithAuthentication):
    path = '/enrollment/education/'
    model = models.CourseEnrollmentByEducation
    order_by = ['education_level']
    csv_filename_slug = u'enrollment-education'

    def generate_data(self, course_id=None):
        course_id = course_id or self.course_id
        G(self.model, course_id=course_id, date=self.date, education_level=self.el1)
        G(self.model, course_id=course_id, date=self.date, education_level=self.el2)
        G(self.model, course_id=course_id, date=self.date - datetime.timedelta(days=2), education_level=self.el2)

    def setUp(self):
        super(CourseEnrollmentByEducationViewTests, self).setUp()
        self.el1 = 'doctorate'
        self.el2 = 'top_secret'
        self.generate_data()

    def format_as_response(self, *args):
        return [
            {'course_id': unicode(ce.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'education_level': ce.education_level, 'created': ce.created.strftime(settings.DATETIME_FORMAT)} for
            ce in args]


class CourseEnrollmentByGenderViewTests(CourseEnrollmentViewTestCaseMixin, DefaultFillTestMixin,
                                        TestCaseWithAuthentication):
    path = '/enrollment/gender/'
    model = models.CourseEnrollmentByGender
    order_by = ['gender']
    csv_filename_slug = u'enrollment-gender'

    def generate_data(self, course_id=None):
        course_id = course_id or self.course_id
        _genders = ['f', 'm', 'o', None]
        days = 2

        for day in range(days):
            for gender in _genders:
                G(self.model,
                  course_id=course_id,
                  date=self.date - datetime.timedelta(days=day),
                  gender=gender,
                  count=100 + day)

    def setUp(self):
        super(CourseEnrollmentByGenderViewTests, self).setUp()
        self.generate_data()

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

    def test_default_fill(self):
        self.destroy_data()

        # Create a single entry for a single gender
        enrollment = G(self.model, course_id=self.course_id, date=self.date, gender='f', count=1)

        # Create the expected data
        _genders = list(genders.ALL)
        _genders.remove(genders.FEMALE)

        expected = self.serialize_enrollment(enrollment)

        for gender in _genders:
            expected[gender] = 0

        expected = [expected]
        self.assertViewReturnsExpectedData(expected)


class CourseEnrollmentViewTests(CourseEnrollmentViewTestCaseMixin, TestCaseWithAuthentication):
    model = models.CourseEnrollmentDaily
    path = '/enrollment'
    csv_filename_slug = u'enrollment'

    def generate_data(self, course_id=None):
        course_id = course_id or self.course_id
        G(self.model, course_id=course_id, date=self.date, count=203)
        G(self.model, course_id=course_id, date=self.date - datetime.timedelta(days=5), count=203)

    def setUp(self):
        super(CourseEnrollmentViewTests, self).setUp()
        self.generate_data()

    def format_as_response(self, *args):
        return [
            {'course_id': unicode(ce.course_id), 'count': ce.count, 'date': ce.date.strftime(settings.DATE_FORMAT),
             'created': ce.created.strftime(settings.DATETIME_FORMAT)}
            for ce in args]


class CourseEnrollmentModeViewTests(CourseEnrollmentViewTestCaseMixin, DefaultFillTestMixin,
                                    TestCaseWithAuthentication):
    model = models.CourseEnrollmentModeDaily
    path = '/enrollment/mode'
    csv_filename_slug = u'enrollment_mode'

    def setUp(self):
        super(CourseEnrollmentModeViewTests, self).setUp()
        self.generate_data()

    def generate_data(self, course_id=None):
        course_id = course_id or self.course_id

        for mode in enrollment_modes.ALL:
            G(self.model, course_id=course_id, date=self.date, mode=mode)

    def serialize_enrollment(self, enrollment):
        # Treat audit as honor
        if enrollment.mode is enrollment_modes.AUDIT:
            enrollment.mode = enrollment_modes.HONOR

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

        # Merge the honor and audit modes
        response[enrollment_modes.HONOR] += response[enrollment_modes.AUDIT]
        del response[enrollment_modes.AUDIT]

        response[enrollment_modes.PROFESSIONAL] += response[enrollment_modes.PROFESSIONAL_NO_ID]
        del response[enrollment_modes.PROFESSIONAL_NO_ID]

        response[u'count'] = total
        response[u'cumulative_count'] = cumulative

        return [response]

    def test_default_fill(self):
        self.destroy_data()

        # Create a single entry for a single enrollment mode
        enrollment = G(self.model, course_id=self.course_id, date=self.date, mode=enrollment_modes.AUDIT,
                       count=1, cumulative_count=100)

        # Create the expected data
        modes = list(enrollment_modes.ALL)
        modes.remove(enrollment_modes.AUDIT)
        modes.remove(enrollment_modes.PROFESSIONAL_NO_ID)

        expected = {}
        for mode in modes:
            expected[mode] = 0

        expected.update(self.serialize_enrollment(enrollment))
        expected[u'count'] = 1
        expected[u'cumulative_count'] = 100

        expected = [expected]
        self.assertViewReturnsExpectedData(expected)


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

    def generate_data(self, course_id=None):
        course_id = course_id or self.course_id
        G(self.model, course_id=course_id, country_code='US', count=455, date=self.date)
        G(self.model, course_id=course_id, country_code='CA', count=356, date=self.date)
        G(self.model, course_id=course_id, country_code='IN', count=12, date=self.date - datetime.timedelta(days=29))
        G(self.model, course_id=course_id, country_code='', count=356, date=self.date)
        G(self.model, course_id=course_id, country_code='A1', count=1, date=self.date)
        G(self.model, course_id=course_id, country_code='A2', count=2, date=self.date)
        G(self.model, course_id=course_id, country_code='AP', count=1, date=self.date)
        G(self.model, course_id=course_id, country_code='EU', count=4, date=self.date)
        G(self.model, course_id=course_id, country_code='O1', count=7, date=self.date)

    def setUp(self):
        super(CourseEnrollmentByLocationViewTests, self).setUp()
        self.country = get_country('US')
        self.generate_data()


class CourseActivityWeeklyViewTests(CourseViewTestCaseMixin, TestCaseWithAuthentication):
    path = '/activity/'
    default_order_by = 'interval_end'
    model = CourseActivityWeekly
    # activity_types = ['ACTIVE', 'ATTEMPTED_PROBLEM', 'PLAYED_VIDEO', 'POSTED_FORUM']
    activity_types = ['ACTIVE', 'ATTEMPTED_PROBLEM', 'PLAYED_VIDEO']
    csv_filename_slug = u'engagement-activity'

    def generate_data(self, course_id=None):
        course_id = course_id or self.course_id

        for activity_type in self.activity_types:
            G(CourseActivityWeekly,
              course_id=course_id,
              interval_start=self.interval_start,
              interval_end=self.interval_end,
              activity_type=activity_type,
              count=100)

    def setUp(self):
        super(CourseActivityWeeklyViewTests, self).setUp()
        self.interval_start = datetime.datetime(2014, 1, 1, tzinfo=pytz.utc)
        self.interval_end = self.interval_start + datetime.timedelta(weeks=1)

        self.generate_data()

    def get_latest_data(self, course_id=None):
        course_id = course_id or self.course_id
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

    def test_get_with_intervals(self):
        """ Verify the endpoint returns multiple data points when supplied with an interval of dates. """
        # Create additional data
        interval_start = self.interval_start + datetime.timedelta(weeks=1)
        interval_end = self.interval_end + datetime.timedelta(weeks=1)

        for activity_type in self.activity_types:
            G(CourseActivityWeekly,
              course_id=self.course_id,
              interval_start=interval_start,
              interval_end=interval_end,
              activity_type=activity_type,
              count=200)

        expected = self.format_as_response(*self.model.objects.all())
        self.assertEqual(len(expected), 2)
        self.assertIntervalFilteringWorks(expected, self.interval_start, interval_end + datetime.timedelta(days=1))


class CourseProblemsListViewTests(DemoCourseMixin, TestCaseWithAuthentication):
    def _get_data(self, course_id=None):
        """
        Retrieve data for the specified course.
        """

        course_id = course_id or self.course_id
        url = '/api/v0/courses/{}/problems/'.format(course_id)
        return self.authenticated_get(url)

    def test_get(self):
        """
        The view should return data when data exists for the course.
        """

        # This data should never be returned by the tests below because the course_id doesn't match.
        G(models.ProblemFirstLastResponseAnswerDistribution)

        # Create multiple objects here to test the grouping. Add a model with a different module_id to break up the
        # natural order and ensure the view properly sorts the objects before grouping.
        module_id = 'i4x://test/problem/1'
        alt_module_id = 'i4x://test/problem/2'
        created = datetime.datetime.utcnow()
        alt_created = created + datetime.timedelta(seconds=2)
        date_time_format = '%Y-%m-%d %H:%M:%S'

        o1 = G(models.ProblemFirstLastResponseAnswerDistribution, course_id=self.course_id, module_id=module_id,
               correct=True, last_response_count=100, created=created.strftime(date_time_format))
        o2 = G(models.ProblemFirstLastResponseAnswerDistribution, course_id=self.course_id, module_id=alt_module_id,
               correct=True, last_response_count=100, created=created.strftime(date_time_format))
        o3 = G(models.ProblemFirstLastResponseAnswerDistribution, course_id=self.course_id, module_id=module_id,
               correct=False, last_response_count=200, created=alt_created.strftime(date_time_format))

        expected = [
            {
                'module_id': module_id,
                'total_submissions': 150,
                'correct_submissions': 50,
                'part_ids': [o1.part_id, o3.part_id],
                'created': alt_created.strftime(settings.DATETIME_FORMAT)
            },
            {
                'module_id': alt_module_id,
                'total_submissions': 100,
                'correct_submissions': 100,
                'part_ids': [o2.part_id],
                'created': created.strftime(settings.DATETIME_FORMAT)
            }
        ]

        response = self._get_data(self.course_id)
        self.assertEquals(response.status_code, 200)
        self.assertListEqual(response.data, expected)

    def test_get_404(self):
        """
        The view should return 404 if no data exists for the course.
        """

        response = self._get_data('foo/bar/course')
        self.assertEquals(response.status_code, 404)


class CourseUsersListTests(DemoCourseMixin, TestCaseWithAuthentication):
    def test_get_list(self):
        date_value = timezone.now()
        bob = G(
            models.UserProfile,
            id=2000,
            username="bob",
            last_login=date_value,
            date_joined=date_value,
            email="bob@example.com",
            name="Bob Loblaw",
            year_of_birth=1789,
        )
        alexa = G(
            models.UserProfile,
            id=2001,
            username="alexa",
            last_login=date_value,
            date_joined=date_value,
            email="alexa@example.com",
            name="Alexa Anderson",
            gender_raw="f",
            year_of_birth=1987,
        )
        # Enroll the above users:
        G(models.CourseEnrollmentSnapshot, user=bob, course_id=self.course_id)
        G(models.CourseEnrollmentSnapshot, user=alexa, course_id=self.course_id)
        # And add another user that won't be enrolled in the demo course:
        G(
            models.UserProfile,
            id=2002,
            username="other",
            last_login=date_value,
            date_joined=date_value,
            email="other@example.com",
            name="Other Manning",
        )

        expected = [
            {
                "id": 2000,
                "username": "bob",
                "last_login": date_value,
                "date_joined": date_value,
                "is_staff": False,
                "email": "bob@example.com",
                "name": "Bob Loblaw",
                "gender": "unknown",
                "year_of_birth": 1789,
                "level_of_education": "unknown"
            },
            {
                "id": 2001,
                "username": "alexa",
                "last_login": date_value,
                "date_joined": date_value,
                "is_staff": False,
                "email": "alexa@example.com",
                "name": "Alexa Anderson",
                "gender": "female",
                "year_of_birth": 1987,
                "level_of_education": "unknown"
            },
        ]
        response = self.authenticated_get('/api/v0/courses/{}/users/'.format(self.course_id))
        self.assertEquals(response.status_code, 200)
        self.assertIsInstance(response.data, dict)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['previous'], None)
        self.assertEqual(response.data['next'], None)
        self.assertListEqual(response.data['results'], expected)


class CourseVideosListViewTests(DemoCourseMixin, TestCaseWithAuthentication):
    def _get_data(self, course_id=None):
        """
        Retrieve videos for a specified course.
        """
        course_id = course_id or self.course_id
        url = '/api/v0/courses/{}/videos/'.format(course_id)
        return self.authenticated_get(url)

    def test_get(self):
        # add a blank row, which shouldn't be included in results
        G(models.Video)

        module_id = 'i4x-test-video-1'
        video_id = 'v1d30'
        created = datetime.datetime.utcnow()
        date_time_format = '%Y-%m-%d %H:%M:%S'
        G(models.Video, course_id=self.course_id, encoded_module_id=module_id,
          pipeline_video_id=video_id, duration=100, segment_length=1, users_at_start=50, users_at_end=10,
          created=created.strftime(date_time_format))

        alt_module_id = 'i4x-test-video-2'
        alt_video_id = 'a1d30'
        alt_created = created + datetime.timedelta(seconds=10)
        G(models.Video, course_id=self.course_id, encoded_module_id=alt_module_id,
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

        response = self._get_data(self.course_id)
        self.assertEquals(response.status_code, 200)
        self.assertListEqual(response.data, expected)

    def test_get_404(self):
        response = self._get_data('foo/bar/course')
        self.assertEquals(response.status_code, 404)
