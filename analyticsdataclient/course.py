

class Course(object):

    """Course scoped analytics."""

    # TODO: Should we have an acceptance test that runs the hadoop job to populate the database, serves the data with
    # the API server and uses the client to retrieve it and validate the various transports?

    def __init__(self, client, course_key):
        """
        Initialize the CourseUserActivity.

        Arguments:

            client (analyticsdataclient.client.Client): The client to use to access remote resources.
            course_key (mixed): An object that when passed to unicode() returns the unique identifier for the course as
                it is represented in the data pipeline results.

        """
        self.client = client
        self.course_key = course_key

    @property
    def recent_active_user_count(self):
        """A count of users who have recently interacted with the course in any way."""
        # TODO: should we return something more structured than a python dict?
        return self.client.get('courses/{0}/recent_activity'.format(unicode(self.course_key)))

    @property
    def recent_problem_activity_count(self):
        """A count of users who have recently attempted a problem."""
        # TODO: Can we avoid passing around strings like "ATTEMPTED_PROBLEM" in the data pipeline and the client?
        return self.client.get(
            'courses/{0}/recent_activity?label=ATTEMPTED_PROBLEM'.format(unicode(self.course_key)))
