from __future__ import absolute_import

import collections
import datetime

import pytz

from analytics_data_api.v0 import models
from django_dynamic_fixture import G


def flatten(dictionary, parent_key='', sep='.'):
    """
    Flatten dictionary

    http://stackoverflow.com/a/6027615
    """
    items = []
    for key, value in dictionary.items():
        new_key = parent_key + sep + key if parent_key else key
        if isinstance(value, collections.MutableMapping):
            items.extend(list(flatten(value, new_key).items()))
        else:
            items.append((new_key, value))
    return dict(items)


def create_engagement(course_id, username, entity_type, event_type, entity_id, count, date=None):
    """Create a ModuleEngagement model"""
    if date is None:
        date = datetime.datetime(2015, 1, 1, tzinfo=pytz.utc)
    G(
        models.ModuleEngagement,
        course_id=course_id,
        username=username,
        date=date,
        entity_type=entity_type,
        entity_id=entity_id,
        event=event_type,
        count=count,
        created=date,
    )
