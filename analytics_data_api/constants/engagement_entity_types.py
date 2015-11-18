DISCUSSION = 'discussion'
PROBLEM = 'problem'
VIDEO = 'video'
INDIVIDUAL_TYPES = [DISCUSSION, PROBLEM, VIDEO]

DISCUSSIONS = 'discussions'
PROBLEMS = 'problems'
VIDEOS = 'videos'
AGGREGATE_TYPES = [DISCUSSIONS, PROBLEMS, VIDEOS]

# useful for agregating ModuleEngagement to ModuleEngagementTimeline
SINGULAR_TO_PLURAL = {
    DISCUSSION: DISCUSSIONS,
    PROBLEM: PROBLEMS,
    VIDEO: VIDEOS,
}
