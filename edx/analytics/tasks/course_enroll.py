"""
Luigi tasks for extracting course enrollment statistics from tracking log files.

Example command lines:

 (local)

  python course_enroll.py --local-scheduler CourseEnrollmentTotalsPerDay
        --name mytest --src input --include 'tracking*' --include '2012*'
        --dest output7

 (local using s3)

  python course_enroll.py --local-scheduler CourseEnrollmentTotalsPerDay
        --name mytest --src s3://edx-analytics-test-data/data --include 'tracking*'
        --dest s3://edx-analytics-scratch/output

"""
import sys

import luigi
import luigi.hadoop
import luigi.s3
import luigi.hdfs

import edx.analytics.util.eventlog as eventlog
from edx.analytics.tasks.pathutil import get_target_for_url, PathSetTask

import logging
logger = logging.getLogger(__name__)


################################
# Task Map-Reduce definitions
################################


class CourseEnrollmentEventsPerDayMixin(object):
    """Calculates daily change in enrollment for a user in a course, given raw event log input."""

    def mapper(self, line):
        """
        Generates output values for explicit enrollment events.

        Args:

          line: text line from a tracking event log.

        Yields:

          (course_id, user_id), (timestamp, action_value)

            where `timestamp` is in ISO format, with resolution to the millisecond
            and `action_value` = 1 (enrolled) or -1 (unenrolled).

        Example:
            (edX/DemoX/Demo_Course, dummy_userid), (2013-09-10T00:01:05, 1)
        """
        parsed_tuple_or_none = get_explicit_enrollment_output(line)
        if parsed_tuple_or_none is not None:
            yield parsed_tuple_or_none

    def reducer(self, key, values):
        """
        Calculate status for each user on the end of each day where they changed their status.

        Args:

          key:  (course_id, user_id) tuple
          value:  (timestamp, action_value) tuple

        Yields:

          (course_id, datestamp), enrollment_change

            where `datestamp` is in ISO format, with resolution to the day
            and `enrollment_change` is the change on that date for an individual user.
            Produced values are -1 or 1.

        No output is yielded if a user enrolls and then unenrolls (or unenrolls and
        then enrolls) on a given day.  Only days with a change at the end of the day
        when compared with the previous day are output.

        Note that we don't bother to actually output the user_id,
        since it's not needed downstream (though it might be sometimes useful
        for debugging). 

        Example:
            (edX/DemoX/Demo_Course, 2013-09-10), 1
            (edX/DemoX/Demo_Course, 2013-09-12), -1

        """
        # sys.stderr.write("Found key in reducer: " + str(key) + '\n')
        course_id, user_id = key

        # Sort input values (by timestamp) to easily detect the end of a day.
        # Note that this assumes the timestamp values (strings) are in ISO
        # representation, so that the tuples will be ordered in ascending time value.
        sorted_values = sorted(values)

        # Convert timestamps to dates, so we can group them by day.
        func = eventlog.timestamp_to_datestamp
        values = [(func(timestamp), value) for timestamp, value in sorted_values]

        # Add a stop item to ensure we process the last entry.
        values = values + [(None, None)]

        # The enrollment state for each student: {1 : enrolled, -1: unenrolled}
        # Assume students start in an unknown state, so that whatever happens on
        # the first day will get output.
        state, prev_state = 0, 0

        prev_date = None
        for (this_date, action) in values:
            # Before we process a new date, report the state if it has
            # changed from the previously reported, if any.
            if this_date != prev_date and prev_date is not None:
                if state != prev_state:
                    # sys.stderr.write("outputting date and value: " + str(prev_date) + " " + str(state)  + '\n')
                    prev_state = state
                    yield (course_id, prev_date), state

            # sys.stderr.write("accumulating date and value: " + str(this_date) + " " + str(action) + '\n')
            # Consecutive changes of the same kind don't affect the state.
            if action != state:
                state = action
            else:
                sys.stderr.write("WARNING: duplicate enrollment event {action} "
                    "for user_id {user_id} in course {course_id} on {date}".format(
                    action=action, user_id=user_id, course_id=course_id, date=this_date))

            # If this is the first entry, then we need to infer what
            # the previous state was before the first entry arrives.
            # For this, we take the opposite of the first entry.
            if prev_date is None:
                prev_state = -1 if action == 1 else 1

            prev_date = this_date


class CourseEnrollmentChangesPerDayMixin(object):
    """Calculates daily changes in enrollment, given per-user net changes by date."""

    def mapper(self, line):
        """
        Args:  tab-delimited values in a single text line

        Yields:  (course_id, datestamp), enrollment_change

        Example:
            (edX/DemoX/Demo_Course, 2013-09-10), 1
            (edX/DemoX/Demo_Course, 2013-09-12), -1

        """
        course_id, date, enrollment_change = line.split('\t')
        yield (course_id, date), enrollment_change

    def reducer(self, key, values):
        """
        Reducer: sums enrollments for a given course on a particular date.

        Args:

          (course_id, datestamp), enrollment_changes

          Input `enrollment_changes` are the enrollment changes on a day due to a specific user.
          Each user with a change has a separate input, either -1 (unenroll) or 1 (enroll).

        Yields:

          (course_id, datestamp), enrollment_change

          Output `enrollment_change` is summed across all users, one output per course.

        """
        # sys.stderr.write("Found key in second reducer: " + str(key) + '\n')
        count = sum(int(v) for v in values)
        yield key, count


##################################
# Task requires/output definitions
##################################

class BaseCourseEnrollmentTask(luigi.hadoop.JobTask):
    """
    Base class for course enrollment calculations.

    Parameters:

      name: a unique identifier to distinguish one run from another.  It is used in
          the construction of output filenames, so each run will have distinct outputs.
      src:  a URL to the root location of input tracking log files.
      dest:  a URL to the root location to write output file(s).
      include:  a list of patterns to be used to match input files, relative to `src` URL.
          The default value is ['*'].
      run_locally: a boolean flag to indicate that the task should be run locally rather than
          on a hadoop cluster.  This is used only to change the intepretation of S3 URLs in src and/or dest.
    """
    name = luigi.Parameter()
    src = luigi.Parameter()
    dest = luigi.Parameter()
    include = luigi.Parameter(is_list=True, default=('*',))
    run_locally = luigi.BooleanParameter()

    def extra_modules(self):
        # The following are needed for (almost) every course enrollment task.
        # Boto is used for S3 access, cjson for parsing log files, and util
        # is used for parsing events and date conversion.
        import boto
        import cjson
        import edx.analytics.util
        return [boto, edx.analytics.util, cjson]


class CourseEnrollmentEventsPerDay(CourseEnrollmentEventsPerDayMixin, BaseCourseEnrollmentTask):
    """Calculates daily change in enrollment for a user in a course, given raw event log input."""

    def requires(self):
        return PathSetTask(self.src, self.include, self.run_locally)

    def output(self):
        # generate a single output file
        output_name = 'course_enrollment_events_per_day_{name}'.format(name=self.name)
        return get_target_for_url(self.dest, output_name, self.run_locally)


class CourseEnrollmentChangesPerDay(CourseEnrollmentChangesPerDayMixin, BaseCourseEnrollmentTask):
    """Calculates daily changes in enrollment, given per-user net changes by date."""

    def requires(self):
        return CourseEnrollmentEventsPerDay(self.name, self.src, self.dest, self.include, self.run_locally)

    def output(self):
        # generate a single output file
        output_name = 'course_enrollment_changes_per_day_{name}'.format(name=self.name)
        return get_target_for_url(self.dest, output_name, self.run_locally)


class FirstCourseEnrollmentEventsPerDay(CourseEnrollmentEventsPerDayMixin, BaseCourseEnrollmentTask):
    """Calculate number of "first" course enrollments per-user, per-course, per-day."""

    def requires(self):
        return PathSetTask(self.src, self.include, self.run_locally)

    def output(self):
        # generate a single output file
        output_name = 'first_course_enrollment_events_per_day_{name}'.format(name=self.name)
        return get_target_for_url(self.dest, output_name, self.run_locally)

    def mapper(self, line):
        """
        Generates output values for explicit enrollment events.

        Args:

          line: text line from a tracking event log.

        Yields:

          (course_id, user_id), (timestamp, action_value)

            where action_value = 1 (enrolled) or -1 (unenrolled)
            and timestamp is in ISO format, with resolution to the millisecond.

        Example:
            (edX/DemoX/Demo_Course, dummy_userid), (2013-09-10T00:01:05, 1)

        """
        parsed_tuple_or_none = get_explicit_enrollment_output(line)
        if parsed_tuple_or_none is not None:
            yield parsed_tuple_or_none

    def reducer(self, key, values):
        """
        Calculate first time each user enrolls in a course.

        Output key:   (course_id, date)
        Output value:  1 on the first date the user enrolls.

        Note that we don't bother to actually output the user_id,
        since it's not needed downstream.

        Example:
            edX/DemoX/Demo_Course	2013-09-10	1

        """
        # sys.stderr.write("Found key in reducer: " + str(key) + '\n')
        course_id, _user_id = key
        sorted_values = sorted(values)
        for (timestamp, change_value) in sorted_values:
            # get the day's date from the event's timestamp:
            this_date = eventlog.get_datestamp_from_timestamp(timestamp)
            # if it's an enrollment, output it and we're done.
            if change_value > 0:
                yield (course_id, this_date), change_value
                return


class FirstCourseEnrollmentChangesPerDay(CourseEnrollmentChangesPerDayMixin, BaseCourseEnrollmentTask):
    """Calculate changes in "first" course enrollments per-course, per-day."""

    def requires(self):
        return FirstCourseEnrollmentEventsPerDay(self.name, self.src, self.dest, self.include, self.run_locally)

    def output(self):
        # generate a single output file
        output_name = 'first_course_enrollment_changes_per_day_{name}'.format(name=self.name)
        return get_target_for_url(self.dest, output_name, self.run_locally)


################################
# Helper methods

################################

def get_explicit_enrollment_output(line):
    """
    Generates output values for explicit enrollment events.

    Args:

      line: text line from a tracking event log.

    Returns:

      (course_id, user_id), (timestamp, action_value)

        where action_value = 1 (enrolled) or -1 (unenrolled)
        and timestamp is in ISO format, with resolution to the millisecond.

      or None if there is no valid enrollment event on the line.

    Example:
            (edX/DemoX/Demo_Course, dummy_userid), (2013-09-10T00:01:05, 1)

    """
    # Before parsing, check that the line contains something that
    # suggests it's an enrollment event.
    if 'edx.course.enrollment' not in line:
        return None

    # try to parse the line into a dict:
    item = eventlog.parse_eventlog_item(line)
    if item is None:
        # The line didn't parse.  For this specific purpose,
        # we can assume that all enrollment-related lines would parse,
        # and these non-parsing lines would get skipped anyway.
        return None

    # get event type, and check that it exists:
    event_type = item.get('event_type')
    if event_type is None:
        eventlog.log_item("encountered event with no event_type", item)
        return None

    # convert the type to a value:
    if event_type == 'edx.course.enrollment.activated':
        action_value = 1
    elif event_type == 'edx.course.enrollment.deactivated':
        action_value = -1
    else:
        # not an enrollment event...
        return None

    # get the timestamp:
    datetime = eventlog.get_event_time(item)
    if datetime is None:
        eventlog.log_item("encountered event with bad datetime", item)
        return None
    timestamp = eventlog.datetime_to_timestamp(datetime)

    # Use the `user_id` from the event `data` field, since the
    # `user_id` in the `context` field is the user who made the
    # request but not necessarily the one who got enrolled.  (The
    # `course_id` should be the same in `context` as in `data`.)

    # Get the event data:
    event_data = eventlog.get_event_data(item)
    if event_data is None:
        # Assume it's already logged (and with more specifics).
        return None

    # Get the course_id from the data, and validate.
    course_id = event_data['course_id']
    if not eventlog.is_valid_course_id(course_id):
        eventlog.log_item("encountered explicit enrollment event with bogus course_id", item)
        return None

    # Get the user_id from the data:
    user_id = event_data.get('user_id')
    if user_id is None:
        eventlog.log_item("encountered explicit enrollment event with no user_id", item)
        return None

    # For now, ignore the enrollment 'mode' (e.g. 'honor').

    return (course_id, user_id), (timestamp, action_value)


################################
# Running tasks
################################


def main():
    """Mainline for command-line testing."""
    luigi.run()


if __name__ == '__main__':
    main()
