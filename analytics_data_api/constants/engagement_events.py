from analytics_data_api.constants import engagement_entity_types

CREATED = 'created'
RESPONDED = 'responded'
COMMENTED = 'commented'

ATTEMPTED = 'attempted'
COMPLETED = 'completed'

PLAYED = 'played'

# map entity types to events
EVENTS = {
    engagement_entity_types.FORUM: [CREATED, RESPONDED, COMMENTED],
    engagement_entity_types.PROBLEM: [ATTEMPTED, COMPLETED],
    engagement_entity_types.VIDEO: [PLAYED],
}
