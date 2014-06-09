

class Course(object):


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
    def user_activity(self):
        return self.client.get('user_activity?course_id={0}'.format(unicode(self.course_key)))
