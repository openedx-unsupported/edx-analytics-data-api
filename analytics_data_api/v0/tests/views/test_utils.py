import ddt
from mock import Mock

from django.http import Http404
from django.test import TestCase

from analytics_data_api.v0.exceptions import CourseKeyMalformedError
from analytics_data_api.v0.tests.views import CourseSamples
import analytics_data_api.v0.views.utils as utils


@ddt.ddt
class UtilsTest(TestCase):

    @ddt.data(
        None,
        'not-a-key',
    )
    def test_invalid_course_id(self, course_id):
        with self.assertRaises(CourseKeyMalformedError):
            utils.validate_course_id(course_id)

    @ddt.data(*CourseSamples.course_ids)
    def test_valid_course_id(self, course_id):
        try:
            utils.validate_course_id(course_id)
        except CourseKeyMalformedError:
            self.fail('Unexpected CourseKeyMalformedError!')

    def test_split_query_argument_none(self):
        self.assertIsNone(utils.split_query_argument(None))

    @ddt.data(
        ('one', ['one']),
        ('one,two', ['one', 'two']),
    )
    @ddt.unpack
    def test_split_query_argument(self, query_args, expected):
        self.assertListEqual(utils.split_query_argument(query_args), expected)

    def test_raise_404_if_none_raises_error(self):
        decorated_func = utils.raise_404_if_none(Mock(return_value=None))
        with self.assertRaises(Http404):
            decorated_func(self)

    def test_raise_404_if_none_passes_through(self):
        decorated_func = utils.raise_404_if_none(Mock(return_value='Not a 404'))
        self.assertEqual(decorated_func(self), 'Not a 404')
