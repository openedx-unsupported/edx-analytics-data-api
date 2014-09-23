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

       $ ./manage.py syncdb --migrate --noinput
       $ ./manage.py syncdb --migrate --noinput --database=analytics

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
.. |coverage-status| image:: https://coveralls.io/repos/edx/edx-analytics-data-api/badge.png
   :target: https://coveralls.io/r/edx/edx-analytics-data-api
