

class Course(object):

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
    def active_users_last_week(self):
        # TODO: should we return something more structured than a python dict?
        return self.client.get('courses/{0}/activity_last_week'.format(unicode(self.course_key)))

    @property
    def users_attempted_problems_last_week(self):
        # TODO: Can we avoid passing around strings like "Attempted_Problem" in the data pipeline and the client?
        return self.client.get(
            'courses/{0}/activity_last_week?label=Attempted_Problem'.format(unicode(self.course_key)))
