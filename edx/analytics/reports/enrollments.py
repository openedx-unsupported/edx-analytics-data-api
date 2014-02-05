"""Enrollment related reports"""

import csv
from datetime import timedelta

import luigi
import luigi.hdfs

import numpy
import pandas


class EnrollmentsByWeek(luigi.Task):
    """Calculates cumulative enrollments per week per course.

    Parameters:
        source: Location of daily enrollments per date. The format is a hadoop
            tsv file, with fields course_id, date and count.
        destination: Location of the resulting report. The output format is a
            excel csv file with course_id and one column per requested week.
        offsets: Location of seed values for each course. The format is a
            hadoop tsv file, with fields course_id, date and offset.
        date: End date of the last week requested.
        weeks: Number of weeks from the end date to request.

    Output:
        Excel CSV file with one row per course. The columns are
        the cumulative enrollments counts for each week requested.

    """

    source = luigi.Parameter()
    destination = luigi.Parameter()
    offsets = luigi.Parameter(default=None)
    date = luigi.DateParameter()
    weeks = luigi.IntParameter(default=10)

    def requires(self):
        results = {'source': ExternalURL(self.source)}
        if self.offsets:
            results.update({'offsets': ExternalURL(self.offsets)})

        return results

    def output(self):
        return get_target_from_url(self.destination)

    def run(self):
        # Load the data into a pandas dataframe
        count_by_day = self.read_source()

        offsets = self.read_offsets()
        if offsets is not None:
            self.include_offsets(count_by_day, offsets)

        cumulative_by_week = self.accumulate(count_by_day)

        with self.output().open('w') as output_file:
            self.save_output(cumulative_by_week, output_file)

    def read_source(self):
        """
        Read source into a pandas DataFrame.

        Returns:
            Pandas dataframe with one column per course_id. Indexed
            for the time interval available in the source data.

        """
        with self.input()['source'].open('r') as input_file:
            data = self.read_tsv(input_file)

            # Reorganize the data. One column per course_id, with
            # shared date index.
            data = data.pivot(index='date',
                              columns='course_id',
                              values='count')

            # Complete the range of data to include all days between
            # the dates of the first and last events.
            date_range = pandas.date_range(min(data.index), max(data.index))
            data = data.reindex(date_range)
            data = data.fillna(0)

        return data

    def read_offsets(self):
        """
        Read offsets into a pandas DataFrame.

        Returns:
            Pandas dataframe with one row per course_id and
            columns for the date and count of the offset.

            Returns None if no offset was specified.

        """

        data = None

        if self.input().get('offsets'):
            with self.input()['offsets'].open('r') as offset_file:
                data = self.read_tsv(offset_file)

        return data

    def read_tsv(self, input_file):
        """Read hadoop formatted tsv file into a pandas DataFrame."""

        names = ['course_id', 'date', 'count']

        # Not assuming any encoding, course_id will be read as plain string
        data = pandas.read_csv(input_file,
                               names=names,
                               quoting=csv.QUOTE_NONE,
                               encoding=None,
                               delimiter='\t')

        data.date = pandas.to_datetime(data.date)
        return data

    def include_offsets(self, count_by_day, offsets):
        """
        Add offsets to a dataframe inplace.

        Args:
            count_by_day: Dataframe with format from `read_source`
            offsets: Dataframe with format from `read_offsets`.

        """

        for n, (course_id, date, count) in offsets.iterrows():
            if course_id in count_by_day.columns:
                # The offsets are computed to begining of that day. We
                # add them to the counts by the end of that day to
                # get the correct count for the day.
                count_by_day.loc[date, course_id] += count

                # Flag values before the offset day with NaN,
                # since they are not "available".
                not_available = count_by_day.index < date
                count_by_day.loc[not_available, course_id] = numpy.NaN

    def accumulate(self, count_by_day):
        # Calculate the cumulative sum per day of the input.
        # Entries with NaN stay NaN.
        # At this stage only the data prior to the offset should contain NaN.
        cumulative_sum = count_by_day.cumsum()

        # List the dates of the last day of each week requested.
        start, weeks = self.date, self.weeks
        days = [start - timedelta(i*7) for i in reversed(xrange(0, weeks))]

        # Sample the cumulative data on the requested days.
        # Result is NaN if there is no data available for that date.
        results = cumulative_sum.loc[days]

        return results

    def save_output(self, results, output_file):
        # Make a row per course_id
        results = results.transpose()

        # List of fieldnames for the report
        fieldnames = ['course_id'] + list(results.columns)

        writer = csv.DictWriter(output_file, fieldnames)
        writer.writerow(dict((k, k) for k in fieldnames))  # Write header

        def format_counts(counts_dict):
            for k, v in counts_dict.iteritems():
                yield k, '-' if numpy.isnan(v) else int(v)

        for index, series in results.iterrows():
            values = {'course_id': index}
            by_week_values = format_counts(series.to_dict())
            values.update(by_week_values)
            writer.writerow(values)


class ExternalURL(luigi.ExternalTask):
    """Simple Task that returns a target based on its URL"""
    url = luigi.Parameter()

    def output(self):
        return get_target_from_url(self.url)


def get_target_from_url(url):
    """Returns a luigi target based on the url scheme"""
    # TODO: Make external utility to resolve target by URL,
    # including s3, s3n, etc.
    if url.startswith('hdfs://') or url.startswith('s3://'):
        if url.endswith('/'):
            return luigi.hdfs.HdfsTarget(url, format=luigi.hdfs.PlainDir)
        else:
            return luigi.hdfs.HdfsTarget(url)
    else:
        return luigi.LocalTarget(url)
