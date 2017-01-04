edX Analytics API Server |build-status| |coverage-status|
=========================================================

This repository includes the Django server for the API as well as the
API package itself. The client is hosted at
https://github.com/edx/edx-analytics-data-api-client.

License
-------

The code in this repository is licensed under version 3 of the AGPL
unless otherwise noted.

Please see ``LICENSE.txt`` for details.

Getting Started
---------------

1. Install the requirements:

   ::

       $ make develop

2. Setup the databases:

   ::

       $ ./manage.py migrate --noinput
       $ ./manage.py migrate --noinput --database=analytics

   The learner API endpoints require elasticsearch with a mapping
   defined on this `wiki page <https://openedx.atlassian.net/wiki/display/AN/Learner+Analytics#LearnerAnalytics-ElasticSearch>`_.
   The connection to elasticsearch can be configured by the
   ``ELASTICSEARCH_LEARNERS_HOST`` and
   ``ELASTICSEARCH_LEARNERS_INDEX`` django settings.  For testing, you
   can install elasticsearch locally:

   ::

      $ make test.install_elasticsearch

   To run the cluster for testing:

   ::

      $ make test.run_elasticsearch

3. Create a user and authentication token. Note that the user will be
   created if one does not exist.

   ::

       $ ./manage.py set_api_key <username> <token>

4. Run the server:

   ::

       $ ./manage.py runserver

Loading Data
------------

The fixtures directory contains demo data and the
``generate_fake_enrollment_data`` management command can generate
enrollment data. Run the command below to load/generate this data in the
database.

::

        $ make loaddata

Loading Video Data
~~~~~~~~~~~~~~~~~~

The above command should work fine on its own, but you may see warnings about
video ids:

::

        WARNING:analyticsdataserver.clients:Course Blocks API failed to return
        video ids (401). See README for instructions on how to authenticate the
        API with your local LMS.

In order to generate video data, the API has to be authenticated with
your local LMS so that it can access the video ids for each course. Instead of
adding a whole OAuth client to the API for this one procedure, we will piggyback
off of the Insights OAuth client by taking the OAuth token it generates and
using it here.

1. Start your local LMS server. (e.g. in devstack, run `paver devstack --fast lms`).

2. If your local LMS server is running on any address other than the default of
   `http://localhost:8000/`, make sure to add this setting to
   `analyticsdataserver/settings/local.py` with the correct URL. (you will
   likely not need to do this):

   ::

      # Don't forget to add the trailing forward slash
      LMS_BASE_URL = 'http://example.com:8000/'

3. Sign into your local Insights server making sure to use your local LMS for
   authentication. This will generate a new OAuth access token if you do not
   already have one that isn't expired.

   The user you sign in with must have staff access to the courses for which you
   want generated video data.

4. Visit your local LMS server's admin site (by default, this is at
   `http://localhost:8000/admin`).

5. Sign in with a superuser account. Don't have one? Make one with this command
   in your devstack as the `edxapp` user:

   ::
   
      $ edxapp@precise64:~/edx-platform$ ./manage.py lms createsuperuser
   
   Enter a username and password that you will remember.

6. On the admin site, find the "Oauth2" section and click the link "Access
   tokens". The breadcrumbs should show "Home > Oauth2 > Access tokens".

   Copy the string in the "Token" column for the first row in the table. Also,
   make sure the "User" of the first row is the same user that you signed in
   with in step 3.

7. Paste the string as a new setting in `analyticsdataserver/settings/local.py`:

   ::

      COURSE_BLOCK_API_AUTH_TOKEN = '<paste access token here>'

8. Run `make loaddata` again and ensure that you see the following log message
   in the output:

   ::

      INFO:analyticsdataserver.clients:Successfully authenticated with the
      Course Blocks API.

9. Check if you now have video data in the API. Either by querying the API in
   the swagger docs at `/docs/#!/api/Videos_List_GET`, or visiting the Insights
   `engagement/videos/` page for a course.
   
Note: the access tokens expire in one year so you should only have to follow the
above steps once a year.

Running Tests
-------------

Run ``make validate`` install the requirements, run the tests, and run
lint.

How to Contribute
-----------------

Contributions are very welcome, but for legal reasons, you must submit a
signed `individual contributor’s agreement`_ before we can accept your
contribution. See our `CONTRIBUTING`_ file for more information – it
also contains guidelines for how to maintain high code quality, which
will make your contribution more likely to be accepted.

.. _individual contributor’s agreement: http://code.edx.org/individual-contributor-agreement.pdf
.. _CONTRIBUTING: https://github.com/edx/edx-platform/blob/master/CONTRIBUTING.rst

.. |build-status| image:: https://travis-ci.org/edx/edx-analytics-data-api.svg?branch=master
   :target: https://travis-ci.org/edx/edx-analytics-data-api
.. |coverage-status| image:: https://img.shields.io/codecov/c/github/edx/edx-analytics-data-api/master.svg
   :target: https://codecov.io/gh/edx/edx-analytics-data-api
