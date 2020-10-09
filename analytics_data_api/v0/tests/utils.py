import collections
import datetime

import enterprise_data
import pytz
from django_dynamic_fixture import G

from analytics_data_api.v0 import models


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


def create_enterprise_user(enterprise_customer_uuid, username, enterprise_user_id=1000):
    """Create EnterpriseUser model data"""
    G(
        enterprise_data.models.EnterpriseUser,
        enterprise_id=enterprise_customer_uuid,
        lms_user_id=1,
        enterprise_user_id=enterprise_user_id,
        user_username=username,
    )
