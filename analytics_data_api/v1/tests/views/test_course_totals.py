import random
from urllib import quote_plus

import ddt
from django_dynamic_fixture import G

from analytics_data_api.v1 import models
from analytics_data_api.v1.tests.views import CourseSamples
from analyticsdataserver.tests import TestCaseWithAuthentication


@ddt.ddt
class CourseTotalsViewTests(TestCaseWithAuthentication):

    SEED_DATA_BOUNDS = (10000, 100000)
    OPTIONAL_COURSE_MODES = ['honor', 'credit', 'professional', 'professional-no-id']

    @classmethod
    def _get_counts(cls):
        """
        Returns a triplet of viable (count, cumulative_count, count_change_7_days) numbers
        """
        count = random.randint(CourseTotalsViewTests.SEED_DATA_BOUNDS[0], CourseTotalsViewTests.SEED_DATA_BOUNDS[1])
        cumulative_count = random.randint(count, int(count * 1.5))
        count_change_7_days = random.randint(int(count * .1), int(count * .3))
        return (count, cumulative_count, count_change_7_days)

    @classmethod
    def setUpClass(cls):
        super(CourseTotalsViewTests, cls).setUpClass()
        cls.test_data = {
            id: {
                'count': 0,
                'cumulative_count': 0,
                'verified_enrollment': 0,
                'count_change_7_days': 0
            } for id in CourseSamples.course_ids
        }  # pylint: disable=attribute-defined-outside-init
        for course in cls.test_data:
            modes = ['verified']  # No choice here, everyone gets a verified mode
            modes = modes + random.sample(CourseTotalsViewTests.OPTIONAL_COURSE_MODES, random.randint(1, 3))
            for mode in modes:
                counts = cls._get_counts()
                cls.test_data[course]['count'] += counts[0]
                if mode == 'verified':
                    cls.test_data[course]['verified_enrollment'] += counts[0]
                cls.test_data[course]['cumulative_count'] += counts[1]
                cls.test_data[course]['count_change_7_days'] += counts[2]
                G(
                    models.CourseMetaSummaryEnrollment,
                    course_id=course,
                    enrollment_mode=mode,
                    count=counts[0],
                    cumulative_count=counts[1],
                    count_change_7_days=counts[2]
                )

    def _get_data(self, course_ids):
        url = '/api/v1/course_totals/'
        if course_ids:
            url += '?course_ids={}'.format(",".join(map(quote_plus, course_ids)))
        return self.authenticated_get(url)

    @ddt.data(
        None,
        CourseSamples.course_ids,
        [CourseSamples.course_ids[1]],
        [CourseSamples.course_ids[0], CourseSamples.course_ids[2]]
    )
    def test_get(self, course_ids):
        response = self._get_data(course_ids)  # get response first so we can set expected if course_ids==[]
        if not course_ids:
            course_ids = CourseSamples.course_ids
        expected = {
            'count': sum(
                [self.test_data[course]['count'] for course in course_ids]
            ),
            'cumulative_count': sum(
                [self.test_data[course]['cumulative_count'] for course in course_ids]
            ),
            'verified_enrollment': sum(
                [self.test_data[course]['verified_enrollment'] for course in course_ids]
            ),
            'count_change_7_days': sum(
                [self.test_data[course]['count_change_7_days'] for course in course_ids]
            )
        }
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected)
