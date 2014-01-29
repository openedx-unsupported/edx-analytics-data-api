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

import luigi
import luigi.hadoop
import luigi.s3
import luigi.hdfs

import edx.analytics.util.eventlog as eventlog
from edx.analytics.tasks.pathutil import get_target_for_url, PathSetTask


def get_explicit_enrollment_output(line):
    """
    Generates output values for explicit enrollment events.

    Output format:  (course_id, user_id), (timestamp, action_value)

      where action_value = 1 (enrolled) or -1 (unenrolled)
      and timestamp is in ISO format, with resolution to the second.

    Returns None if there is no valid enrollment event on the line.
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
    datetime = eventlog.get_datetime(item)
    if datetime is None:
        eventlog.log_item("encountered event with bad datetime", item)
        return None
    timestamp = eventlog.get_timestamp(datetime)


    # Enrollment parameters like course_id and user_id may be stored
    # in the context and also in the data.  Pick the data.  For
    # course_id, we expect the values to be the same.  However, for
    # user_id, the values may not be the same.  This is because the
    # context contains the name and id of the user making a particular
    # request, but it is not necessarily the id of the user being
    # enrolled.  For example, Studio provides authors with the ability
    # to add staff to their courses, and these staff get enrolled in
    # the course while the author is listed in the context.

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
    if 'user_id' not in event_data:
        eventlog.log_item("encountered explicit enrollment event with no user_id", item)
        return None
    user_id = event_data['user_id']

    # For now, ignore the enrollment 'mode' (e.g. 'honor').

    return (course_id, user_id), (timestamp, action_value)


################################
# Task Map-Reduce definitions
################################


class BaseCourseEnrollmentEventsPerDay(luigi.hadoop.JobTask):
    """Calculates daily change in enrollment for a user in a course, given raw event log input."""

    def mapper(self, line):
        """
        Output format:  (course_id, username), (datetime, action_value)

          where action_value = 1 (enrolled) or -1 (unenrolled)

        Example:
            edX/DemoX/Demo_Course	dummyuser	2013-09-10	1
            edX/DemoX/Demo_Course	dummyuser	2013-09-10	1
            edX/DemoX/Demo_Course	dummyuser	2013-09-10     -1

        """
        parsed_tuple = get_explicit_enrollment_output(line)
        if parsed_tuple is not None:
            # sys.stderr.write("Found tuple in mapper: " + str(parsed_tuple) + '\n')
            yield parsed_tuple

    def reducer(self, key, values):
        """
        Calculate status for each user on the end of each day where they changed their status.

        Output key:   (course_id, date)
        Output value:  net enrollment change on that date for an individual user.
             Expected values are -1, 0 (no change), 1

        Note that we don't bother to actually output the username,
        since it's not needed downstream.

        If the user were already enrolled (or attempted enrollment),
        the net change from a subsequent enrollment is zero.  Same to
        unenroll after an unenroll.  This is true whether they occur
        on the same day or on widely disparate days.  For implicit
        enrollment events, we don't know when they succeed, so we
        assume they succeed the first time, and ignore subsequent
        attempts.  Likewise for implicit enrollment events followed by
        explicit enrollment events.

        An unenroll following an enroll on the same day will also
        result in zero change.

        Example:
            edX/DemoX/Demo_Course	2013-09-10	1
            edX/DemoX/Demo_Course	2013-09-10     -1
            edX/DemoX/Demo_Course	2013-09-10      0

        """
        # sys.stderr.write("Found key in reducer: " + str(key) + '\n')
        course_id, username = key

        # Sort input values (by timestamp) to easily detect the end of a day.
        sorted_values = sorted(values)

        # Convert timestamps to dates, so we can group them by day.
        fn = eventlog.get_datestamp_from_timestamp
        values = [(fn(timestamp), value) for timestamp, value in sorted_values]

        # Add a stop item to ensure we process the last entry.
        values = values + [(None, None)]

        # The enrollment state for each student: {1 : enrolled, -1: unenrolled}
        # Assume students start in an unknown state, so that whatever happens on
        # the first day will get output.
        state, prev_state = 0, 0

        prev_date = None
        import sys
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

            # If this is the first entry, then we need to infer what
            # the previous state was before the first entry arrives.
            # For this, we take the opposite of the first entry.
            if prev_date is None:
                prev_state = -1 if action == 1 else 1

            prev_date = this_date

class BaseCourseEnrollmentChangesPerDay(luigi.hadoop.JobTask):
    """Calculates daily changes in enrollment, given per-user net changes by date."""

    def mapper(self, line):
        """
        Output key:   (course_id, date)
        Output value:  net enrollment change on that date for an individual user.
             Expected values are -1, 0 (no change), 1

        Example:
            edX/DemoX/Demo_Course	2013-09-10	1
            edX/DemoX/Demo_Course	2013-09-10     -1
            edX/DemoX/Demo_Course	2013-09-10      0

        """
        # yield line
        inputs = line.split('\t')
        if len(inputs) == 3:
            yield (inputs[0], inputs[1]), inputs[2]

    def reducer(self, key, values):
        """
        Reducer: sums enrollments for a given course on a particular date.

        Inputs are enrollments changes on a day due to a specific user.
        Outputs are enrollment changes on a day summed across all users.

        Key:   (course_id, date)
        Values:  individual enrollment changes, represented as -1 or 1.

        Output key:  (course_id, date)
        Output value:  sum(changes)
        """
        # sys.stderr.write("Found key in second reducer: " + str(key) + '\n')
        count = 0
        for value in values:
            count += int(value)
        yield key, count


class BaseCourseEnrollmentTotalsPerDay(luigi.hadoop.JobTask):
    """Calculates cumulative changes in enrollment, given net changes by date."""

    def mapper(self, line):
        """
        Key:   course_id
        Values:  (date, net enrollment change on that date)

        Example:  
            edX/DemoX/Demo_Course	2013-09-10	5
            edX/DemoX/Demo_Course	2013-09-11     -3
        """
        # yield line
        inputs = line.split('\t')
        if len(inputs) == 3:
            yield inputs[0], (inputs[1], inputs[2])

    def reducer(self, key, values):
        """
        Reducer: sums enrollments for a given course through a particular date.

        Key:   course_id
        Values:   date, and enrollment changes per day

        Output key:  course_id
        Output value:  date, accum(changes)
        """
        # sys.stderr.write("Found key in third reducer: " + str(key) + '\n')
        sorted_values = sorted(values)
        accum_count = 0
        for date, count in sorted_values:
            accum_count += int(count)
            yield key, date, accum_count


##################################
# Task requires/output definitions
##################################

class CourseEnrollmentEventsPerDay(BaseCourseEnrollmentEventsPerDay):

    name = luigi.Parameter()
    src = luigi.Parameter()
    dest = luigi.Parameter()
    include = luigi.Parameter(is_list=True, default=('*',))
    run_locally = luigi.BooleanParameter()

    def requires(self):
        return PathSetTask(self.src, self.include, self.run_locally)

    def output(self):
        # generate a single output file
        output_name = 'course_enrollment_events_per_day_{name}'.format(name=self.name)
        return get_target_for_url(self.dest, output_name, self.run_locally)

    def extra_modules(self):
        import boto
        import cjson
        import edx.analytics.util
        return [boto, edx.analytics.util, cjson]


class CourseEnrollmentChangesPerDay(BaseCourseEnrollmentChangesPerDay):

    name = luigi.Parameter()
    src = luigi.Parameter()
    dest = luigi.Parameter()
    include = luigi.Parameter(is_list=True, default=('*',))
    run_locally = luigi.BooleanParameter()

    def requires(self):
        return CourseEnrollmentEventsPerDay(self.name, self.src, self.dest, self.include, self.run_locally)

    def output(self):
        # generate a single output file
        output_name = 'course_enrollment_changes_per_day_{name}'.format(name=self.name)
        return get_target_for_url(self.dest, output_name, self.run_locally)

    def extra_modules(self):
        import boto
        import cjson
        import edx.analytics.util
        return [boto, edx.analytics.util, cjson]


class CourseEnrollmentTotalsPerDay(BaseCourseEnrollmentTotalsPerDay):

    name = luigi.Parameter()
    src = luigi.Parameter()
    dest = luigi.Parameter()
    include = luigi.Parameter(is_list=True, default=('*',))
    run_locally = luigi.BooleanParameter()

    def requires(self):
        return CourseEnrollmentChangesPerDay(self.name, self.src, self.dest, self.include, self.run_locally)

    def output(self):
        # generate a single output file
        output_name = 'course_enrollment_totals_per_day_{name}'.format(name=self.name)
        return get_target_for_url(self.dest, output_name, self.run_locally)

    def extra_modules(self):
        import boto
        import cjson
        import edx.analytics.util
        return [boto, edx.analytics.util, cjson]


class FirstCourseEnrollmentEventsPerDay(BaseCourseEnrollmentEventsPerDay):

    name = luigi.Parameter()
    src = luigi.Parameter()
    dest = luigi.Parameter()
    include = luigi.Parameter(is_list=True, default=('*',))
    run_locally = luigi.BooleanParameter()

    def requires(self):
        return PathSetTask(self.src, self.include, self.run_locally)

    def output(self):
        # generate a single output file
        output_name = 'first_course_enrollment_events_per_day_{name}'.format(name=self.name)
        return get_target_for_url(self.dest, output_name, self.run_locally)

    def extra_modules(self):
        import boto
        import cjson
        import edx.analytics.util
        return [boto, edx.analytics.util, cjson]

    def reducer(self, key, values):
        """
        Calculate first time each user enrolls in a course.

        Output key:   (course_id, date)
        Output value:  1 on the first date the user enrolls.

        Note that we don't bother to actually output the username,
        since it's not needed downstream.

        Example:
            edX/DemoX/Demo_Course	2013-09-10	1

        """
        # sys.stderr.write("Found key in reducer: " + str(key) + '\n')
        course_id, username = key
        sorted_values = sorted(values)
        for (timestamp, change_value) in sorted_values:
            # get the day's date from the event's timestamp:
            this_date = eventlog.get_datestamp_from_timestamp(timestamp)
            # if it's an enrollment, output it and we're done.
            if change_value > 0:
                yield (course_id, this_date), change_value
                return


class FirstCourseEnrollmentChangesPerDay(BaseCourseEnrollmentChangesPerDay):

    name = luigi.Parameter()
    src = luigi.Parameter()
    dest = luigi.Parameter()
    include = luigi.Parameter(is_list=True, default=('*',))
    run_locally = luigi.BooleanParameter()

    def requires(self):
        return FirstCourseEnrollmentEventsPerDay(self.name, self.src, self.dest, self.include, self.run_locally)

    def output(self):
        # generate a single output file
        output_name = 'first_course_enrollment_changes_per_day_{name}'.format(name=self.name)
        return get_target_for_url(self.dest, output_name, self.run_locally)

    def extra_modules(self):
        import boto
        import cjson
        import edx.analytics.util
        return [boto, edx.analytics.util, cjson]

################################
# Running tasks
################################


def main():
    luigi.run()


if __name__ == '__main__':
    main()
