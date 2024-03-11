edX Analytics API Server
========================

DEPRECATION NOTICE
------------------

The Insights product and associated repositories are in the process of being
deprecated and removed from service. Details on the deprecation status and
process can be found in the relevant `Github issue <https://github.com/openedx/public-engineering/issues/221>_`.

This repository may be archived and moved to the openedx-unsupported
Github organization at any time.

The following sections are for historical purposes only.

------------------

This repository includes the Django server for the API as well as the
API package itself. The client is hosted at
https://github.com/openedx/edx-analytics-data-api-client.

The enterprise client is hosted at https://github.com/openedx/frontend-app-admin-portal.

License
-------

The code in this repository is licensed under version 3 of the AGPL
unless otherwise noted.

Please see ``LICENSE.txt`` for details.

Getting Started With Devstack
-----------------------------
The best way to run this service is with edX Devstack: https://github.com/openedx/devstack.

See the `Devstack Readme <https://github.com/openedx/devstack/blob/master/README.rst>`_ for information on how to install and run devstack.

With devstack running and this repo checked-out locally, you'll want to do the following from your devstack directory:

   ::

      $ make dev.pull.analyticsapi
      $ make dev.up.analyticsapi
      $ make dev.provision.analyticsapi     # this will provision the DB user, run migrations, etc.
      $ docker-compose restart analyticsapi # maybe necessary to reset the DB connection
      $ make analyticsapi-logs              # make sure the app is running without errors


Getting Started Standalone (deprecated, prefer running in devstack)
-------------------------------------------------------------------
#. Create a virtual environment and activate it.

#. Install the requirements:

   ::

       $ make develop

#. Setup the databases:

   ::

       $ make migrate-all

   The learner API endpoints require elasticsearch with a mapping
   defined on this `wiki page <https://openedx.atlassian.net/wiki/display/AN/Learner+Analytics#LearnerAnalytics-ElasticSearch>`_.
   The connection to elasticsearch can be configured by the
   ``ELASTICSEARCH_LEARNERS_HOST`` and
   ``ELASTICSEARCH_LEARNERS_INDEX`` django settings. To run tests locally use:

   ::

      $ make test

   This will launch an Elasticsearch Docker container for the tests. To simply run the container without starting
   the tests, run:

   ::

      $ make test.run_elasticsearch

   To stop an Elasticsearch Docker container, run:

   ::

      $ make test.stop_elasticsearch

#. Create a user and authentication token. Note that the user will be
   created if one does not exist.

   ::

       $ ./manage.py set_api_key <username> <token>

#. Run the server:

   ::

       $ ./manage.py runserver

.. _JDK 1.8: https://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html

Development with edx-enterprise-data
------------------------------------
If you need to make changes to ``edx-enterprise-data`` and have them reflected when you run the ``edx-analytics-data-api`` server,
you can follow these steps. If you do not intend to make changes to ``edx-enterprise-data``, you can skip this section.

Devstack Development
~~~~~~~~~~~~~~~~~~~~
#. Clone the `edx-enterprise-data <https://github.com/openedx/edx-enterprise-data>`_ repo into the ``src`` folder alongside your devstack
workspace on the host system.
#. The modified ``edx-enterprise-data`` repository will now be available to devstack containers at ``/edx/src/edx-enterprise-data``.
#. Inside the ``edx-data-analytics-api`` container run `pip install `-e /edx/src/edx-enterprise-data``

Standalone Development
~~~~~~~~~~~~~~~~~~~~~~
#. Recommended: Install this repo into a subfolder of your working directory. Within that subfolder create an ``src`` folder.
#. Clone the `edx-enterprise-data <https://github.com/openedx/edx-enterprise-data>`_ repo into the ``src`` folder.
#. ``cd`` into your ``edx-data-analytics-api`` folder and activate your virtualenv.
#. Run ``pip install -e ./src/edx-enterprise-data``.
#. Run the server as per instructions above. Changes to ``edx-enterprise-data`` should be picked up by the server.

Loading Data
------------

The fixtures directory contains demo data and the
``generate_fake_enrollment_data`` management command can generate
enrollment data. Run the command below to load/generate this data in the
database.

::

        $ make loaddata

Additional management commands for creating data can be found in `edx-enterprise-data <https://github.com/openedx/edx-enterprise-data>`_

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
   `http://localhost:18000/`, make sure to add this setting to
   `analyticsdataserver/settings/local.py` with the correct URL. (you will
   likely not need to do this):

   ::

      # Don't forget to add the trailing forward slash
      LMS_BASE_URL = 'http://example.com:18000/'

3. Sign into your local Insights server making sure to use your local LMS for
   authentication. This will generate a new OAuth access token if you do not
   already have one that isn't expired.

   The user you sign in with must have staff access to the courses for which you
   want generated video data.

4. Visit your local LMS server's admin site (by default, this is at
   `http://localhost:18000/admin`).

5. Sign in with a superuser account. Don't have one? Make one with this command
   in your devstack as the `edxapp` user:

   ::

      $ edxapp@precise64:~/edx-platform$ ./manage.py lms createsuperuser

   Enter a username and password that you will remember.

6. On the admin site, find the "Django OAuth Toolkit" section and click the link "Access
   tokens". The breadcrumbs should show "Home > Django OAuth Toolkit > Access tokens".

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
