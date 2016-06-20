from analytics_data_api.constants.engagement_events import (ATTEMPTED, ATTEMPTS_PER_COMPLETED, COMPLETED,
                                                            CONTRIBUTED, DISCUSSION, PROBLEM, VIDEO, VIEWED)


class EngagementType(object):
    """
    Encapsulates:
        - The API consumer-facing display name for engagement types
        - The internal question of whether the metric should be counted in terms
          of the entity type or the raw number of events.
    """
    # Defines the current canonical set of engagement types used in the Learner
    # Analytics API.
    ALL_TYPES = (
        'problem_attempts_per_completed',
        'problems_attempted',
        'problems_completed',
        'videos_viewed',
        'discussion_contributions',
    )

    def __init__(self, entity_type, event_type):
        """
        Initializes an EngagementType for a particular entity and event type.

        Arguments:
            entity_type (str): the type of module interacted with
            event_type (str): the type of interaction on that entity
        """
        if entity_type == PROBLEM:
            if event_type == ATTEMPTED:
                self.name = 'problems_attempted'
                self.is_counted_by_entity = True
            if event_type == ATTEMPTS_PER_COMPLETED:
                self.name = 'problem_attempts_per_completed'
                self.is_counted_by_entity = True
            if event_type == COMPLETED:
                self.name = 'problems_completed'
                self.is_counted_by_entity = True
        elif entity_type == VIDEO:
            if event_type == VIEWED:
                self.name = 'videos_viewed'
                self.is_counted_by_entity = True
        elif entity_type == DISCUSSION:
            if event_type == CONTRIBUTED:
                # Note that the discussion contribution metric counts
                # total discussion contributions, not number of
                # discussions contributed to.
                self.name = 'discussion_contributions'
                self.is_counted_by_entity = False
        else:
            raise ValueError(
                'No display name found for entity type "{entity_type}" and event type "{event_type}"'.format(
                    entity_type=entity_type,
                    event_type=event_type,
                )
            )
