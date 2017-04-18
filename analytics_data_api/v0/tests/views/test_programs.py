import datetime
import ddt
from django_dynamic_fixture import G

from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.tests.views import CourseSamples, APIListViewTestMixin
from analyticsdataserver.tests import TestCaseWithAuthentication


@ddt.ddt
class ProgramsViewTests(TestCaseWithAuthentication, APIListViewTestMixin):
    model = models.CourseProgramMetadata
    model_id = 'program_id'
    serializer = serializers.CourseProgramMetadataSerializer
    expected_programs = []
    list_name = 'programs'
    default_ids = CourseSamples.program_ids

    def setUp(self):
        super(ProgramsViewTests, self).setUp()
        self.now = datetime.datetime.utcnow()
        self.maxDiff = None
        self.course_id = CourseSamples.course_ids[0]

    def tearDown(self):
        self.model.objects.all().delete()

    def create_model(self, model_id):
        G(self.model, course_id=self.course_id, program_id=model_id, program_type='Demo', program_title='Test')

    def expected_result(self, item_id):
        """Expected program metadata to populate with data."""
        program = super(ProgramsViewTests, self).expected_result(item_id)
        program.update([
            ('program_type', 'Demo'),
            ('program_title', 'Test'),
            ('course_ids', [self.course_id])
        ])
        return program

    @ddt.data(
        None,
        CourseSamples.program_ids,
        ['not-real-program'].extend(CourseSamples.program_ids),
    )
    def test_all_programs(self, program_ids):
        self._test_all_items(program_ids)

    @ddt.data(*CourseSamples.program_ids)
    def test_one_course(self, program_id):
        self._test_one_item(program_id)

    @ddt.data(
        ['program_id'],
        ['program_type', 'program_title'],
    )
    def test_fields(self, fields):
        self._test_fields(fields)
