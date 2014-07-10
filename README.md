edX Analytics API Server
========================

This repository includes the Django server for the API as well as the API package itself. The client is hosted at
https://github.com/edx/edx-analytics-api-client.

License
-------
The code in this repository is licensed under version 3 of the AGPL unless otherwise noted.

Please see `LICENSE.txt` for details.

Getting Started
---------------

1. Install the requirements:
 
        $ make develop
        
2. Setup the databases:

        $ ./manage.py syncdb --migrate --noinput
        $ ./manage.py syncdb --migrate --noinput --database=analytics

3. Create a user and authentication token. Note that the user will be created if one does not exist.

        $ ./manage.py set_api_key <username> <token>

4. Run the server:

        $ ./manage.py runserver

Loading Data
------------
The fixtures directory contains demo data. This data can be loaded with the following commands:

        $ ./manage.py syncdb --migrate --noinput --database=analytics
        $ ./manage.py loaddata courses education_levels single_course_activity course_enrollment_birth_year course_enrollment_education course_enrollment_gender --database=analytics

Running Tests
-------------

Run `make validate` install the requirements, run the tests, and run lint.
