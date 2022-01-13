import ddt
from django.conf import settings
from rest_framework import status

from analytics_data_api.constants.engagement_events import (
    ATTEMPTED,
    COMPLETED,
    CONTRIBUTED,
    DISCUSSION,
    PROBLEM,
    VIDEO,
    VIEWED,
)
from analytics_data_api.tests.test_utils import set_databases
from analytics_data_api.v0.tests.utils import create_engagement, create_enterprise_user
from analytics_data_api.v0.tests.views import CourseSamples
from analyticsdataserver.tests.utils import TestCaseWithAuthentication

PAGINATED_SAMPLE_DATA = [
    {
        'entity_id': 'entity-id',
        'created': '2015-01-01T00:00:00Z',
        'course_id': 'edX/DemoX/Demo_Course',
        'username': 'death_stroke',
        'entity_type': 'problem',
        'count': 5,
        'id': 1,
        'event': 'attempted',
        'date': '2015-01-01'
    },
    {
        'entity_id': 'entity-id',
        'created': '2015-01-01T00:00:00Z',
        'course_id': 'edX/DemoX/Demo_Course',
        'username': 'death_stroke',
        'entity_type': 'problem',
        'count': 3,
        'id': 2,
        'event': 'completed',
        'date': '2015-01-01'
    },
    {
        'entity_id': 'entity-id',
        'created': '2015-01-01T00:00:00Z',
        'course_id': 'edX/DemoX/Demo_Course',
        'username': 'death_stroke',
        'entity_type': 'video',
        'count': 7,
        'id': 4,
        'event': 'viewed',
        'date': '2015-01-01'
    }
]


@ddt.ddt
@set_databases
class EnterpriseLearnerEngagementViewTests(TestCaseWithAuthentication):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.default_username = 'death_stroke'
        cls.enterprise_customer_uuid = '5c0dd495-e726-46fa-a6a8-2d8d26c716c9'
        cls.path = f'/api/v0/enterprise/{cls.enterprise_customer_uuid}/engagements/'

        create_enterprise_user(cls.enterprise_customer_uuid, cls.default_username)
        create_engagement(CourseSamples.course_ids[0], cls.default_username, PROBLEM, ATTEMPTED, 'entity-id', 5)
        create_engagement(CourseSamples.course_ids[0], cls.default_username, PROBLEM, COMPLETED, 'entity-id', 3)
        create_engagement(CourseSamples.course_ids[0], cls.default_username, DISCUSSION, CONTRIBUTED, 'entity-id', 2)
        create_engagement(CourseSamples.course_ids[0], cls.default_username, VIDEO, VIEWED, 'entity-id', 7)

    def test_enterprise_learner_engagements(self):
        """
        Test learner engagment view.
        """
        response = self.authenticated_get(self.path)
        assert response.status_code == status.HTTP_200_OK
        response = response.json()

        # verify that not allowed engagement entity_type is not present in api response
        for learner_engagment in response['results']:
            assert learner_engagment['entity_type'] not in settings.EXCLUDED_ENGAGEMENT_ENTITY_TYPES

        assert response == {
            'results': PAGINATED_SAMPLE_DATA,
            'num_pages': 1,
            'next': None,
            'previous': None,
            'count': 3
        }

    @ddt.data(
        (1, 1),
        (2, 1),
        (3, 1),
    )
    @ddt.unpack
    def test_enterprise_learner_engagements_paginatation(self, page, page_size):
        """
        Test learner engagment view for paginated response.
        """
        path = f'{self.path}?page={page}&page_size={page_size}'
        response = self.authenticated_get(path)
        assert response.status_code == status.HTTP_200_OK
        response = response.json()
        assert len(response['results']) == 1
        assert response['results'][0] == PAGINATED_SAMPLE_DATA[page - 1]
