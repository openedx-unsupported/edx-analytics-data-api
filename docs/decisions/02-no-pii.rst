2. Only Aggregated Learner Data In Analytics
--------------------------------------------

Status
------

Accepted

Context
-------

Most endpoints in the analytics data API provide aggregate user data. The exceptions are the learner and engagement timeline calls which provide individual learner data. That data goes on to populate the Insights learner view. That learner view includes username, email address, and individual performance information.

Peronally identifiable information (PII) belonging to learners requires more careful treatment than aggregated learner data. Individual performance is also more sensitive than averages or aggregates. These pieces of data are more sensitive not only in the UI but during every stage of the analytics pipeline.

Since the learner view is the most expensive to support and one of the least used we are deprecating it. That creates an opportunity to better define what analytics data is allowed.

Decision
--------

The analytics API will not contain any personally identifiable learner information such as names or emails. Further, the analytics API will only provide aggregate or average information across a class of learners.

Consequences
------------

Learner view and API deprecation is already underway. In addition we will deprecate the user engagement view which uses the same analytics database tables.

This decision constrains future analytics work to only aggregate data. If we want to expose individual learner data to instructors, we will use a different channel with access control appropriate to more sensitive information.


References
----------

- `Learner view removal discussion <https://discuss.openedx.org/t/deprecation-removal-learner-view-in-insights-data-api-and-analytics-pipeline/6788>`_
- `Learner view DEPR ticket <https://github.com/openedx/public-engineering/issues/36>`_
