.. _Video Data API:

###############
Video Data API
###############

.. contents:: Section Contents 
  :local:
  :depth: 1

.. _Get the Timeline for a Video:

***************************************
Get the Timeline for a Video
***************************************

.. autoclass:: analytics_data_api.v0.views.videos.VideoTimelineView 

**Example Response**

.. code-block:: json

    HTTP 200 OK  
    Vary: Accept   
    Content-Type: text/html; charset=utf-8   
    Allow: GET, HEAD, OPTIONS 

    [
      {
        "segment": 0,
        "num_users": 472,
        "num_views": 539,
        "created": "2015-05-13T050419"
      },
      {
        "segment": 1,
        "num_users": 450,
        "num_views": 510,
        "created": "2015-05-13T050419"
      },
      {
        "segment": 2,
        "num_users": 438,
        "num_views": 493,
        "created": "2015-05-13T050419"
      }
    ]
