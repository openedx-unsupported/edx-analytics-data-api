#######################
Course Information API
#######################

.. contents:: Section Contents 
  :local:
  :depth: 1
  
.. _Get Weekly Course Activity:

***************************
Get Weekly Course Activity
***************************

.. autoclass:: analytics_data_api.v0.views.courses.CourseActivityWeeklyView

**Example Response**

.. code-block:: json

    HTTP 200 OK  
    Vary: Accept   
    Content-Type: text/html; charset=utf-8   
    Allow: GET, HEAD, OPTIONS 

    [
      {
        "interval_start": "2014-12-08T000000",
        "interval_end": "2014-12-15T000000",
        "course_id": "edX/DemoX/Demo_Course",
        "any": 3013,
        "attempted_problem": 206,
        "played_video": 1049,
        "created": "2014-12-10T193104"
      }
    ]

.. _Get Recent Course Activity:

***************************
Get Recent Course Activity
***************************

.. autoclass:: analytics_data_api.v0.views.courses.CourseActivityMostRecentWeekView

**Example Response**

.. code-block:: json

    HTTP 200 OK  
    Vary: Accept   
    Content-Type: text/html; charset=utf-8   
    Allow: GET, HEAD, OPTIONS 

    {
      "interval_start": "2014-12-08T00:00:00Z",
      "interval_end": "2014-12-15T00:00:00Z",
      "activity_type": "any",
      "count": 3013,
      "course_id": "edX/DemoX/Demo_Course"
    }

.. _Get the Course Enrollment:

***************************
Get the Course Enrollment
***************************

.. autoclass:: analytics_data_api.v0.views.courses.CourseEnrollmentView

**Example Response**

.. code-block:: json

    HTTP 200 OK  
    Vary: Accept   
    Content-Type: text/html; charset=utf-8   
    Allow: GET, HEAD, OPTIONS 
    [
      {
        "course_id": "edX/DemoX/Demo_Course",
        "date": "2014-12-10",
        "count": 1892,
        "created": "2014-12-10T193146"
      }
    ]

.. _Get the Course Enrollment by Mode:

*********************************
Get the Course Enrollment by Mode
*********************************

.. autoclass:: analytics_data_api.v0.views.courses.CourseEnrollmentModeView

**Example Response**

.. code-block:: json

    HTTP 200 OK  
    Vary: Accept   
    Content-Type: text/html; charset=utf-8   
    Allow: GET, HEAD, OPTIONS 

    [
      {
        "course_id": "edX/DemoX/Demo_Course",
        "date": "2014-12-10",
        "count": 1890,
        "cumulative_count": 1931,
        "created": "2014-12-10T193146",
        "honor": 945,
        "professional": 189,
        "verified": 756
      }
    ]

.. _Get the Course Enrollment by Birth Year:

****************************************
Get the Course Enrollment by Birth Year
****************************************

.. autoclass:: analytics_data_api.v0.views.courses.CourseEnrollmentByBirthYearView

**Example Response**

.. code-block:: json

    HTTP 200 OK  
    Vary: Accept   
    Content-Type: text/html; charset=utf-8   
    Allow: GET, HEAD, OPTIONS 

    [
      {
        "course_id": "edX/DemoX/Demo_Course",
        "date": "2014-12-10",
        "birth_year": 1960,
        "count": 11,
        "created": "2014-12-10T193146"
      },
      {
        "course_id": "edX/DemoX/Demo_Course",
        "date": "2014-12-10",
        "birth_year": 1961,
        "count": 58,
        "created": "2014-12-10T193146"
      }
    ]

.. _Get the Course Enrollment by Education Level:

************************************************
Get the Course Enrollment by Education Level
************************************************

.. autoclass:: analytics_data_api.v0.views.courses.CourseEnrollmentByEducationView

**Example Response**

.. code-block:: json

    HTTP 200 OK  
    Vary: Accept   
    Content-Type: text/html; charset=utf-8   
    Allow: GET, HEAD, OPTIONS 

    [
      {
        "course_id": "edX/DemoX/Demo_Course",
        "date": "2014-12-10",
        "education_level": "bachelors",
        "count": 634,
        "created": "2014-12-10T193146"
      },
      {
        "course_id": "edX/DemoX/Demo_Course",
        "date": "2014-12-10",
        "education_level": "doctorate",
        "count": 88,
        "created": "2014-12-10T193146"
      }
    ]

.. _Get the Course Enrollment by Gender:

************************************************
Get the Course Enrollment by Gender
************************************************

.. autoclass:: analytics_data_api.v0.views.courses.CourseEnrollmentByGenderView

**Example Response**

.. code-block:: json

    HTTP 200 OK  
    Vary: Accept   
    Content-Type: text/html; charset=utf-8   
    Allow: GET, HEAD, OPTIONS 

    [
      {
        "course_id": "edX/DemoX/Demo_Course",
        "date": "2014-12-10",
        "female": 732,
        "male": 1155,
        "other": 435,
        "unknown": 0,
        "created": "2014-12-10T193146"
      }
    ]

.. _Get the Course Enrollment by Location:

************************************************
Get the Course Enrollment by Location
************************************************

.. autoclass:: analytics_data_api.v0.views.courses.CourseEnrollmentByLocationView

See `ISO 3166 country codes`_ for more information.

**Example Response**

.. code-block:: json

    HTTP 200 OK  
    Vary: Accept   
    Content-Type: text/html; charset=utf-8   
    Allow: GET, HEAD, OPTIONS 

    [
      {
        "date": "2014-12-10",
        "course_id": "edX/DemoX/Demo_Course",
        "country": {
          "alpha2": "CA",
          "alpha3": "CAN",
          "name": "Canada"
        },
        "count": 264,
        "created": "2014-12-10T193146"
      },
      {
        "date": "2014-12-10",
        "course_id": "edX/DemoX/Demo_Course",
        "country": {
          "alpha2": "CN",
          "alpha3": "CHN",
          "name": "China"
        },
        "count": 416,
        "created": "2014-12-10T193146"
      }
    ]

.. _Get the Course Video Data:

************************************************
Get the Course Video Data
************************************************

.. autoclass:: analytics_data_api.v0.views.courses.VideosListView

**Example Response**

.. code-block:: json

    HTTP 200 OK  
    Vary: Accept   
    Content-Type: text/html; charset=utf-8   
    Allow: GET, HEAD, OPTIONS 

    [
      {
        "pipeline_video_id": "UniversityX/UX.3.01x/1T2015|i4x-UniversityX-
          UX_3_01x-video-02874e0ae0c74ae7b16faa5d6fdc8085",
        "encoded_module_id": "i4x-UX-UT_3_01x-video-
          02874e0ae0c74ae7b16faa5d6fdc8085",
        "duration": 142,
        "segment_length": 5,
        "users_at_start": 2,
        "users_at_end": 0,
        "created": "2015-04-15T214158"
      },
      {
        "pipeline_video_id": "UniversityX/UX.3.01x/1T2015|i4x-UniversityX-
          UX_3_01x-video-03454e0ae0c72ae7b16fab3d6fdc2143",
        "encoded_module_id": "i4x-UX-UT_3_01x-video-
          03454e0ae0c72ae7b16fab3d6fdc2143",
        "duration": 66,
        "segment_length": 5,
        "users_at_start": 1044,
        "users_at_end": 0,
        "created": "2015-04-15T214158"
      },     
    ]

.. include:: links.rst
