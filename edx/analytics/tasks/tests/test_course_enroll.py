"""
Tests for tasks that collect enrollment events.

"""
import unittest

from edx.analytics.tasks.course_enroll import (
    BaseCourseEnrollmentEventsPerDay,
    BaseCourseEnrollmentChangesPerDay,
    BaseCourseEnrollmentTotalsPerDay,
)

from datetime import datetime




class CourseEnrollEventReduceTest(unittest.TestCase):
    """
    Tests to verify that event log parsing works correctly.
    """
    def setUp(self):
        self.task = BaseCourseEnrollmentEventsPerDay()
        self.key = ('course', 'user')

    def _get_reducer_output(self, values):
        """Run reducer with provided values hardcoded key."""
        return list(self.task.reducer(self.key, values))

    def test_no_events(self):
        self.assertEquals(self._get_reducer_output([]), [])

    def test_single_enrollment(self):
        self.assertEquals(self._get_reducer_output(
            [
                ('2013-01-01T00:00:01', 1),
            ]),
            [
                (('course', '2013-01-01'), 1),
            ])

    def test_single_unenrollment(self):
        self.assertEquals(self._get_reducer_output(
            [
                ('2013-01-01T00:00:01', -1),
            ]),
            [
                (('course', '2013-01-01'), -1),
            ])

    def test_multiple_events_on_same_day(self):
        # run first with no output expected:
        self.assertEquals(self._get_reducer_output(
            [
                ('2013-01-01T00:00:01', 1),
                ('2013-01-01T00:00:02', -1),
                ('2013-01-01T00:00:03', 1),
                ('2013-01-01T00:00:04', -1),
            ]),
            [
            ])
        # then run with output expected:
        self.assertEquals(self._get_reducer_output(
            [
                ('2013-01-01T00:00:01', 1),
                ('2013-01-01T00:00:02', -1),
                ('2013-01-01T00:00:03', -1),
                ('2013-01-01T00:00:04', 1),
            ]),
            [
                (('course', '2013-01-01'), 1),
            ])


    def test_multiple_events_out_of_order(self):
        # Make sure that events are sorted by the reducer.
        self.assertEquals(self._get_reducer_output(
            [
                ('2013-01-01T00:00:04', -1),
                ('2013-01-01T00:00:03', 1),
                ('2013-01-01T00:00:01', 1),
                ('2013-01-01T00:00:02', -1),
            ]),
            [
            ])

    def test_multiple_enroll_events_on_same_day(self):
        self.assertEquals(self._get_reducer_output(
            [
                ('2013-01-01T00:00:01', 1),
                ('2013-01-01T00:00:02', 1),
                ('2013-01-01T00:00:03', 1),
                ('2013-01-01T00:00:04', 1),
            ]),
            [
                (('course', '2013-01-01'), 1),
            ])


    def test_multiple_unenroll_events_on_same_day(self):
        self.assertEquals(self._get_reducer_output(
            [
                ('2013-01-01T00:00:01', -1),
                ('2013-01-01T00:00:02', -1),
                ('2013-01-01T00:00:03', -1),
                ('2013-01-01T00:00:04', -1),
            ]),
            [
                (('course', '2013-01-01'), -1),
            ])

    def test_multiple_enroll_events_on_many_days(self):
        self.assertEquals(self._get_reducer_output(
            [
                ('2013-01-01T00:00:01', 1),
                ('2013-01-01T00:00:02', 1),
                ('2013-01-02T00:00:03', 1),
                ('2013-01-02T00:00:04', 1),
                ('2013-01-04T00:00:05', 1),
            ]),
            [
                (('course', '2013-01-01'), 1),
            ])


    def test_multiple_events_on_many_days(self):
        # Run with an arbitrary list of events.
        self.assertEquals(self._get_reducer_output(
            [
                ('2013-01-01T1',  1),
                ('2013-01-01T2',  -1),
                ('2013-01-01T3',  1),
                ('2013-01-01T4',  -1),
                ('2013-01-02',  1),
                ('2013-01-03',  1),
                ('2013-01-04T1',  1),
                ('2013-01-04T2',  -1),
                ('2013-01-05',  -1),
                ('2013-01-06',  -1),
                ('2013-01-07',  1),
                ('2013-01-08T1',  1),
                ('2013-01-08T2',  1),
                ('2013-01-09T1',  -1),
                ('2013-01-09T2',  -1),
                ]),
            [
                (('course', '2013-01-02'), 1),
                (('course', '2013-01-04'), -1), 
                (('course', '2013-01-07'), 1),
                (('course', '2013-01-09'), -1),
            ])


class CourseEnrollChangesReduceTest(unittest.TestCase):
    """
    Verify that BaseCourseEnrollmentChangesPerDay.reduce() works correctly.
    """
    def setUp(self):
        self.task = BaseCourseEnrollmentChangesPerDay()
        self.key = ('course', '2013-01-01')

    def _get_reducer_output(self, values):
        """Run reducer with provided values hardcoded key."""
        return list(self.task.reducer(self.key, values))

    def test_no_user_counts(self):
        self.assertEquals(self._get_reducer_output([]), [(self.key, 0)])

    def test_single_user_count(self):
        self.assertEquals(self._get_reducer_output([1]), [(self.key, 1)])

    def test_multiple_user_count(self):
        inputs = [1, 1, 1, -1, 1]
        self.assertEquals(self._get_reducer_output(inputs), [(self.key, 3)])


class CourseEnrollTotalsReduceTest(unittest.TestCase):
    """
    Verify that BaseCourseEnrollmentTotalsPerDay.reduce() works correctly.
    """
    def setUp(self):
        self.task = BaseCourseEnrollmentTotalsPerDay()
        self.key = 'course'

    def _get_reducer_output(self, values):
        """Run reducer with provided values hardcoded key."""
        return list(self.task.reducer(self.key, values))

    def test_no_user_counts(self):
        self.assertEquals(self._get_reducer_output([]), [])

    def test_single_user_count(self):
        self.assertEquals(self._get_reducer_output(
            [
                ('2013-01-01', 5),
            ]),
            [
                (self.key, '2013-01-01', 5),
            ])


    def test_multiple_user_count(self):
        self.assertEquals(self._get_reducer_output(
            [
                ('2013-01-01', 5),
                ('2013-01-02', 8),
                ('2013-01-03', 4),
                ('2013-01-04', 9),
            ]),
            [
                (self.key, '2013-01-01', 5),
                (self.key, '2013-01-02', 13),
                (self.key, '2013-01-03', 17),
                (self.key, '2013-01-04', 26),
            ])
