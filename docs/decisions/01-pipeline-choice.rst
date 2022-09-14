1. Pipeline Choice
------------------

Status
------

Accepted

Context
-------

While migrating the analytics pipeline to a new technology, we'd like a toggle which:

- Lets particular users in edX and maybe selected partner organizations see new data
  for validation.
- Is fast for us to flip back and forth to look at new vs. old, ideally without leaving
  the client dashboard.

We also need to make a decision on how to store the new data. In any case, this should
involve a duplicate store to compare the old and new data.

Store Options
-------------

**New tables in original store**

- Least amount of configuration needed.
- Duplicate tables in the same store may get messy. (IE CourseActivity vs V1CourseActivity?)

**Separate store in the same instance**

- Allows for complete duplication with the same table names.
- Cleaner separation of data.

API Options
-----------

**New V1 API**

- Cleaner separation, but there will be duplication of code.
- Easier for us to maintain the original API for Edge and Open edX. (and deprecate later,
  if needed)
- Simple to switch between; we can implement a check on the client dashboard to determine
  which base URL to use.

**Alter the existing API**

- Less code duplication.
- The check for which data to use will have to be passed down from the client to the API.

Decision
--------

To house the new data, we will create a separate database in the same MySQL instance. We
will access this database using a new V1 API, and implement a simple toggle on the client
dashboard to switch between the two APIs.

This toggle can be controlled by a query string (IE `?new_data=true`), and converted to
a Django setting once the new API is fully rolled out.

Consequences
------------

- We will be maintaining two databases and two APIs until the old API is retired (if at all).
- We will rely on the client (in our case,
  `edx-analytics-dashboard <https://github.com/openedx/edx-analytics-dashboard>`_) in order to
  determine which API to use.

References
----------

- `Insights Replumbing <https://2u-internal.atlassian.net/wiki/spaces/PT/pages/15440575/Insights+Replumbing>`_
