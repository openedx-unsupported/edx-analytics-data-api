from analytics_data_api.constants import engagement_entity_types

ATTEMPTED = 'attempted'
ATTEMPTS_PER_COMPLETED = 'attempts_per_completed'
COMPLETED = 'completed'
CONTRIBUTED = 'contributed'
VIEWED = 'viewed'

# map entity types to events
EVENTS = {
    engagement_entity_types.DISCUSSION: [CONTRIBUTED],
    engagement_entity_types.PROBLEM: [ATTEMPTED, ATTEMPTS_PER_COMPLETED, COMPLETED],
    engagement_entity_types.PROBLEMS: [ATTEMPTED, COMPLETED],
    engagement_entity_types.VIDEO: [VIEWED],
    engagement_entity_types.VIDEOS: [VIEWED],
}
