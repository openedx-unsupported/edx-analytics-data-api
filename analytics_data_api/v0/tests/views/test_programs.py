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
    ids_param = 'program_ids'
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

    def generate_data(self, ids=None, course_ids=None, **kwargs):
        """Generate program list data"""
        if ids is None:
            ids = self.default_ids

        if course_ids is None:
            course_ids = [[self.course_id]] * len(ids)

        for item_id, course_id in zip(ids, course_ids):
            self.create_model(item_id, course_ids=course_id, **kwargs)

    def create_model(self, model_id, course_ids=None, **kwargs):
        if course_ids is None:
            course_ids = [self.course_id]

        for course_id in course_ids:
            G(self.model, course_id=course_id, program_id=model_id, program_type='Demo', program_title='Test')

    def all_expected_results(self, ids=None, course_ids=None, **kwargs):
        if ids is None:
            ids = self.default_ids

        if course_ids is None:
            course_ids = [[self.course_id]] * len(ids)

        return [self.expected_result(item_id, course_ids=course_id, **kwargs)
                for item_id, course_id in zip(ids, course_ids)]

    # pylint: disable=arguments-differ
    def expected_result(self, item_id, course_ids=None):
        """Expected program metadata to populate with data."""
        if course_ids is None:
            course_ids = [self.course_id]

        program = super(ProgramsViewTests, self).expected_result(item_id)
        program.update([
            ('program_type', 'Demo'),
            ('program_title', 'Test'),
            ('course_ids', course_ids)
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

    @ddt.data(
        (None, None),
        (CourseSamples.program_ids, [[cid] for cid in CourseSamples.course_ids]),
        (CourseSamples.program_ids, [CourseSamples.course_ids[1:3],
                                     CourseSamples.course_ids[0:2],
                                     CourseSamples.course_ids[0:3]]),
    )
    @ddt.unpack
    def test_all_programs_multi_courses(self, program_ids, course_ids):
        self.generate_data(ids=program_ids, course_ids=course_ids)
        response = self.validated_request(ids=program_ids, exclude=self.always_exclude)
        self.assertEquals(response.status_code, 200)
        self.assertItemsEqual(response.data, self.all_expected_results(ids=program_ids, course_ids=course_ids))
