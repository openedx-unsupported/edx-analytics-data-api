from analytics_data_api.constants import engagement_entity_types

ATTEMPTS = 'attempts'
ATTEMPTED = 'attempted'
COMPLETED = 'completed'
CONTRIBUTED = 'contributed'
VIEWED = 'viewed'

# map entity types to events
EVENTS = {
    engagement_entity_types.DISCUSSIONS: [CONTRIBUTED],
    engagement_entity_types.PROBLEM: [ATTEMPTS],
    engagement_entity_types.PROBLEMS: [ATTEMPTED, COMPLETED],
    engagement_entity_types.VIDEO: [VIEWED],
}
