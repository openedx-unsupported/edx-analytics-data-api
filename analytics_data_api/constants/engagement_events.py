from analytics_data_api.constants import engagement_entity_types

ATTEMPTED = 'attempted'
COMPLETED = 'completed'
CONTRIBUTIONS = 'contributions'
VIEWED = 'viewed'

# map entity types to events
EVENTS = {
    engagement_entity_types.DISCUSSION: [CONTRIBUTIONS],
    engagement_entity_types.PROBLEM: [ATTEMPTED, COMPLETED],
    engagement_entity_types.PROBLEMS: [ATTEMPTED, COMPLETED],
    engagement_entity_types.VIDEO: [VIEWED],
    engagement_entity_types.VIDEOS: [VIEWED],
}
