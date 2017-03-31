import datetime
from collections import OrderedDict
from urllib import urlencode

import ddt
from django_dynamic_fixture import G

from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.tests.views import CourseSamples
from analyticsdataserver.tests import TestCaseWithAuthentication


@ddt.ddt
class ProgramsViewTests(TestCaseWithAuthentication):
    model = models.CourseProgramMetadata
    serializer = serializers.CourseProgramMetadataSerializer
    expected_programs = []

    def setUp(self):
        super(ProgramsViewTests, self).setUp()
        self.now = datetime.datetime.utcnow()
        self.maxDiff = None
        self.course_id = CourseSamples.course_ids[0]

    def tearDown(self):
        self.model.objects.all().delete()

    def path(self, program_ids=None, fields=None, exclude=None):
        query_params = {}
        for query_arg, data in zip(['ids', 'fields', 'exclude'], [program_ids, fields, exclude]):
            if data:
                query_params[query_arg] = ','.join(data)
        query_string = '?{}'.format(urlencode(query_params))
        return '/api/v0/programs/{}'.format(query_string)

    def generate_data(self, program_ids=None):
        """Generate course program data"""
        if program_ids is None:
            program_ids = CourseSamples.program_ids

        for program_id in program_ids:
            G(self.model, course_id=self.course_id, program_id=program_id, program_type='Demo', program_title='Test')

    def expected_program(self, program_id):
        """Expected program metadata to populate with data."""
        program = OrderedDict([
            ('program_id', program_id),
            ('program_type', 'Demo'),
            ('program_title', 'Test'),
        ])
        return program

    def all_expected_programs(self, program_ids=None):
        if program_ids is None:
            program_ids = CourseSamples.program_ids

        return [self.expected_program(program_id) for program_id in program_ids]

    @ddt.data(
        None,
        CourseSamples.program_ids,
        ['not-real-program'].extend(CourseSamples.program_ids),
    )
    def test_all_programs(self, program_ids):
        self.generate_data()
        response = self.authenticated_get(self.path(program_ids=program_ids, exclude=('created',)))
        self.assertEquals(response.status_code, 200)
        expected = sorted(self.all_expected_programs(program_ids=program_ids), key=lambda x: x['program_id'])
        actual = sorted(response.data, key=lambda x: x['program_id'])
        self.assertListEqual(actual, expected)

    @ddt.data(*CourseSamples.program_ids)
    def test_one_course(self, program_id):
        self.generate_data()
        response = self.authenticated_get(self.path(program_ids=[program_id], exclude=('created',)))
        self.assertEquals(response.status_code, 200)
        self.assertItemsEqual(response.data, [self.expected_program(program_id)])

    @ddt.data(
        ['program_id'],
        ['program_type', 'program_title'],
    )
    def test_fields(self, fields):
        self.generate_data()
        response = self.authenticated_get(self.path(fields=fields))
        self.assertEquals(response.status_code, 200)

        # remove fields not requested from expected results
        expected_programs = self.all_expected_programs()
        for expected_program in expected_programs:
            for field_to_remove in set(expected_program.keys()) - set(fields):
                expected_program.pop(field_to_remove)

        self.assertListEqual(response.data, expected_programs)

    def test_no_programs(self):
        response = self.authenticated_get(self.path())
        self.assertEquals(response.status_code, 404)

    def test_no_matching_courses(self):
        self.generate_data()
        response = self.authenticated_get(self.path(program_ids=['no-program-found']))
        self.assertEquals(response.status_code, 404)
