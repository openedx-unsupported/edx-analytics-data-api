########################
Problem Information API
########################

.. contents:: Section Contents 
  :local:
  :depth: 1
  
.. _Get the Grade Distribution for a Course:

***************************************
Get the Grade Distribution for a Course
***************************************

.. autoclass:: analytics_data_api.v0.views.problems.GradeDistributionView 

**Example Response**

.. code-block:: json

    HTTP 200 OK  
    Vary: Accept   
    Content-Type: text/html; charset=utf-8   
    Allow: GET, HEAD, OPTIONS 

    [
      {
        "module_id": "i4x://edX/DemoX/Demo_Course/problem/97fd93e33a18495488578e9e74fa4cae",
        "course_id": "edX/DemoX/Demo_Course",
        "grade": 1,
        "max_grade": 2,
        "count": 5,
        "created": "2014-09-12T114957"
      },
      {
        "module_id": "i4x://edX/DemoX/Demo_Course/problem/97fd93e33a18495488578e9e74fa4cae",
        "course_id": "edX/DemoX/Demo_Course",
        "grade": 2,
        "max_grade": 2,
        "count": 256,
        "created": "2014-09-12T114957"
      }
    ]

.. _Get the Answer Distribution for a Problem:

*******************************************
Get the Answer Distribution for a Problem
*******************************************

.. autoclass:: analytics_data_api.v0.views.problems.ProblemResponseAnswerDistributionView

**Example Response**

.. code-block:: json

    HTTP 200 OK  
    Vary: Accept   
    Content-Type: text/html; charset=utf-8   
    Allow: GET, HEAD, OPTIONS 

    [
       {
         "course_id": "edX/DemoX/Demo_Course",
          "module_id": "i4x://edX/DemoX/Demo_Course/problem/
            268b43628e6d45f79c52453a590f9829",
          "part_id": "i4x-edX-DemoX-Demo_Course-problem-
            268b43628e6d45f79c52453a590f9829_2_1",
          "correct": false,
          "count": 9,
          "value_id": "choice_0",
          "answer_value_text": "Russia",
          "answer_value_numeric": null,
          "problem_display_name": "Multiple Choice Problem",
          "question_text": "Which of the following countries has the largest 
            population?",
          "variant": null,
          "created": "2014-12-05T225026"
        },
        {
         "course_id": "edX/DemoX/Demo_Course",
          "module_id": "i4x://edX/DemoX/Demo_Course/problem/
            268b43628e6d45f79c52453a590f9829",
          "part_id": "i4x-edX-DemoX-Demo_Course-problem-
            268b43628e6d45f79c52453a590f9829_2_1",
          "correct": true,
          "count": 15,
          "value_id": "choice_1",
          "answer_value_text": "Indonesia",
          "answer_value_numeric": null,
          "problem_display_name": "Multiple Choice Problem",
          "question_text": "Which of the following countries has the largest 
            population?",
          "variant": null,
          "created": "2014-12-05T225026"
        }
    ]

.. _Get the View Count for a Subsection:

*************************************
Get the View Count for a Subsection
*************************************

.. autoclass:: analytics_data_api.v0.views.problems.SequentialOpenDistributionView

**Example Response**

.. code-block:: json

    HTTP 200 OK  
    Vary: Accept   
    Content-Type: text/html; charset=utf-8   
    Allow: GET, HEAD, OPTIONS 

    [
      {
        "module_id": "i4x://edX/DemoX/Demo_Course/sequential/5c6c207e16dd47208c29bd8d3e68861e",
        "course_id": "edX/DemoX/Demo_Course",
        "count": 23,
        "created": "2014-09-12T114838"
      }
    ]
