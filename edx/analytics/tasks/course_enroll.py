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


################################
# Task Map-Reduce definitions
################################


class BaseCourseEnrollmentEventsPerDay(luigi.hadoop.JobTask):
    """Calculates daily change in enrollment for a user in a course, given raw event log input."""

    def get_implicit_enrollment_output(self, item):
        """
        Generates output values for implicit enrollment events.

        Output format:  (course_id, username), (datetime, action_value)

          where action_value = 1 (enrolled) or -1 (unenrolled)

        Returns None if the enrollment event on the line is not valid.
        """

        event_data = eventlog.get_event_data(item)
        if event_data is None:
            # Assume it's already logged (and with more specifics).
            return None

        # The args are part of the POST request.  
        # The course_id is stored in a list, so just take the first value:
        post_args = event_data['POST']
        if 'course_id' not in post_args:
            eventlog.log_item("encountered event with no course_id in post args", item)
            return None

        course_id = post_args['course_id'][0]
        if len(course_id) == 0:
            eventlog.log_item("encountered event with zero-length course_id in post args", item)
            return None

        # This is a hack, due to a bug in luigi/hadoop.py:
        # In JobTask.writer(), it calls "\t".join(map(str, flatten(output)))
        # which returns a UnicodeEncodeError when output contains non-ascii characters.
        # For now, just log and skip such course_ids.  Create a separate story in future
        # to make sure that Luigi handles non-ascii characters in general.
        try:
            str(course_id)
        except:
            eventlog.log_item("encountered event with non-ascii course_id in post args", item)
            return None

        # The value of action is expected to be 'enroll' or 'unenroll', but is
        # stored in a list.  We just take the first value (but log if there are more).
        if 'enrollment_action' not in post_args:
            eventlog.log_item("encountered event with no enrollment_action in post args", item)
            return None
        actions = post_args['enrollment_action']
        if len(actions) != 1:
            eventlog.log_item("encountered event with multiple enrollment_actions in post args", item, "WARNING")

        action = actions[0]
        if action == 'enroll':
            action_value = 1 
        elif action == 'unenroll':
            action_value = -1 
        else:
            eventlog.log_item("encountered event with unrecognized value for enrollment_action in post args", item, "WARNING")
            return None

        # get additional data: timestamp and username:
        timestamp = eventlog.get_timestamp(item)
        if timestamp is None:
            # bad format?
            eventlog.log_item("encountered event with bad timestamp", item)
            return None

        if 'username' not in item:
            # bad format?
            eventlog.log_item("encountered implicit enrollment event with no username", item, "WARNING")
            return None

        username = item['username']
        
        return (course_id, username), (eventlog.get_datetime_string(timestamp), action_value)

    def get_explicit_enrollment_output(self, item, event_type):
        """
        Generates output values for explicit enrollment events.

        Output format:  (course_id, username), (datetime, action_value)

          where action_value = 1 (enrolled) or -1 (unenrolled)

        Returns None if the enrollment event on the line is not valid.
        """
        # convert the type to a value:
        if event_type == 'edx.course.enrollment.activated':
            action_value = 1
        elif event_type == 'edx.course.enrollment.deactivated':
            action_value = -1

        # Data is stored in the context, but it's also in the data.
        # Pick one.
        event_data = eventlog.get_event_data(item)
        if event_data is None:
            # Assume it's already logged (and with more specifics).
            return None

        course_id = event_data['course_id']
        # for now, ignore the enrollment 'mode' (e.g. 'honor')

        # get additional data:
        timestamp = eventlog.get_timestamp(item)
        if timestamp is None:
            # bad format?
            eventlog.log_item("encountered event with bad timestamp", item)
            return None

        # there is also a user_id in the event_data, but who knows if
        # it's the same as the username?  But for old events, we don't have
        # such a user_id, and I don't think we're planning on loading such a mapping.
        if 'username' not in item:
            # bad format?
            eventlog.log_item("encountered explicit enrollment event with no username", item)
            return None
        username = item['username']
        
        return (course_id, username), (eventlog.get_datetime_string(timestamp), action_value)


    def get_enrollment_event(self, line):
        """
        Generates output values for explicit enrollment events.

        Output format:  (course_id, username), (datetime, action_value)

          where action_value = 1 (enrolled) or -1 (unenrolled)

        Returns None if there is no enrollment event on the line.
        """
        # Before parsing, check that the line contains something that
        # suggests it's an enrollment event.
        if 'edx.course.enrollment' not in line and '/change_enrollment' not in line:
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

        # check if it is an 'explicit' enrollment event:
        if (event_type == 'edx.course.enrollment.activated' or 
            event_type == 'edx.course.enrollment.deactivated'):
            return self.get_explicit_enrollment_output(item, event_type)

        # check if it is an 'implicit' enrollment event:
        if event_type == '/change_enrollment':
            return self.get_implicit_enrollment_output(item)

        # Not an enrollment event...
        return None

    def mapper(self, line):
        """
        Output format:  (course_id, username), (datetime, action_value)

          where action_value = 1 (enrolled) or -1 (unenrolled)

        Example:
            edX/DemoX/Demo_Course	dummyuser	2013-09-10	1
            edX/DemoX/Demo_Course	dummyuser	2013-09-10	1
            edX/DemoX/Demo_Course	dummyuser	2013-09-10     -1

        """
        parsed_tuple = self.get_enrollment_event(line)
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
        sorted_values = sorted(values)
        prev_date = None
        prev_change = 0
        net_change = 0

        for (datetime, change_value) in sorted_values:
            # get the day's date from the event timestamp:
            this_date = eventlog.get_date_from_datetime(datetime)
            # if the date is different, then output the previous date:
            if this_date != prev_date and prev_date is not None:
                # sys.stderr.write("outputting date and value: " + str(prev_date) + " " + str(net_change)  + '\n')
                yield (course_id, prev_date), net_change
                net_change = 0

            # sys.stderr.write("accumulating date and value: " + str(this_date) + " " + str(change_value) + '\n')
            # accumulate the new numbers:
            prev_date = this_date
            if change_value != prev_change:
                net_change += change_value
                prev_change = change_value

        if prev_date is not None:
            yield (course_id, prev_date), net_change


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
        sum_value = 0
        for value in values:
            sum_value += int(value)
        yield key, sum_value


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
        for (datetime, change_value) in sorted_values:
            # get the day's date from the event timestamp:
            this_date = eventlog.get_date_from_datetime(datetime)
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


class FirstCourseEnrollmentTotalsPerDay(BaseCourseEnrollmentTotalsPerDay):

    name = luigi.Parameter()
    src = luigi.Parameter()
    dest = luigi.Parameter()
    include = luigi.Parameter(is_list=True, default=('*',))
    run_locally = luigi.BooleanParameter()

    def requires(self):
        return FirstCourseEnrollmentChangesPerDay(self.name, self.src, self.dest, self.include, self.run_locally)

    def output(self):
        # generate a single output file
        output_name = 'first_course_enrollment_totals_per_day_{name}'.format(name=self.name)
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
    import argparse
    import boto
    import cjson
    luigi.hadoop.attach(boto, argparse, cjson)
    luigi.run()


if __name__ == '__main__':
    main()
