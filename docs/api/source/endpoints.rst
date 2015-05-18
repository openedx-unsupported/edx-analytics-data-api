.. _Data Analytics API:

#################################
edX Data Analytics API Endpoints
#################################

The edX Platform API allows you to view information about users and their course enrollments, course information, and videos and transcripts.

The following tasks and endpoints are currently supported. 


.. list-table::
   :widths: 10 70
   :header-rows: 1

   * - To:
     - Use this endpoint:
   * - :ref:`Get Weekly Course Activity`
     - /api/v0/courses/{course_id}/activity/
   * - :ref:`Get Recent Course Activity`
     - /api/v0/courses/{course_id}/recent_activity/
   * - :ref:`Get the Course Enrollment`
     - /api/v0/courses/{course_id}/enrollment/  
   * - :ref:`Get the Course Enrollment by Mode`
     - /api/v0/courses/{course_id}/enrollment/mode/
   * - :ref:`Get the Course Enrollment by Birth Year`
     - /api/v0/courses/{course_id}/enrollment/birth_year/ 
   * - :ref:`Get the Course Enrollment by Education Level`
     - /api/v0/courses/{course_id}/enrollment/education/
   * - :ref:`Get the Course Enrollment by Gender`
     - /api/v0/courses/{course_id}/enrollment/gender/ 
   * - :ref:`Get the Course Enrollment by Location`
     - /api/v0/courses/{course_id}/enrollment/location/
   * - :ref:`Get the Course Video Data`
     - /api/v0/courses/{course_id}/videos/
   * - :ref:`Get the Grade Distribution for a Course`
     - /api/v0/problems/{problem_id}/grade_distribution
   * - :ref:`Get the Answer Distribution for a Problem`
     - /api/v0/problems/{problem_id}/answer_distribution
   * - :ref:`Get the View Count for a Subsection`
     - /api/v0/problems/{module_id}/sequential_open_distribution
   * - :ref:`Get the Timeline for a Video`
     - /api/v0/videos/{video_id}/timeline/
   