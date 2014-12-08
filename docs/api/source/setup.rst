.. _Set up the Data Analytics API Server:

######################################
Set up the Data Analytics API Server
######################################

This chapter describes how to set up and test the edX Data Analytics API
server:

#. `Get the Repository`_
#. `Install Server Requirements`_
#. `Run the Server`_
#. `Load Sample Data`_
#. `Test the Data Analytics API`_

Also see :ref:`edX Data Analytics API Authentication`.

**************************
Get the Repository
**************************

You must get the `Data Analytics API repository`_ from GitHub.

From the terminal, enter:

``git clone https://github.com/edx/edx-analytics-data-api``

You may choose to get the repository in a virtual environment.


****************************
Install Server Requirements
****************************

From the terminal at the top level of the server repository, enter:

``$ make develop``

Server requirements are then installed.

****************************
Run the Server
****************************

From the terminal at the top level of the server repository, enter:

``$ ./manage.py runserver``

The server starts.

****************************
Load Sample Data
****************************

From the terminal at the top level of the server repository, enter:

``$ make loaddata``

****************************
Test the Data Analytics API
****************************

After you load sample data and run the server, you can test the API.

#. In a browser, go to: ``http://<server-name>:<port>/docs/#!/api/``

#. Enter a valid key and click **Explore**.

   See :ref:`edX Data Analytics API Authentication` for information on keys.

   You see an interactive list of API endpoints, which you can use to get
   responses with the sample data. Expand the **api** section to see the
   available endpoints.

   .. image:: images/api_test.png
    :alt: The API test web page

3. Expand the section for an endpoint:

   .. image:: images/api_test_expand.png
    :alt: The API test web page with an expanded endpoint

4. Enter parameters as needed and click **Try it out**. The response opens:

   .. image:: images/api_test_response.png
     :alt: The API test web page with a response

To get the sample enrollment data, use ``edX/DemoX/Demo_Course`` as the
``course_id``.

.. include:: links.rst