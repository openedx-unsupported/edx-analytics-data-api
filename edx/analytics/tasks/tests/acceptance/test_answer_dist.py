"""
End to end test of answer distribution.
"""

import os
import logging

from luigi.s3 import S3Client, S3Target

from edx.analytics.tasks.tests.acceptance import AcceptanceTestCase
from edx.analytics.tasks.url import url_path_join


log = logging.getLogger(__name__)


class AnswerDistributionAcceptanceTest(AcceptanceTestCase):

    INPUT_FILE = 'answer_dist_acceptance_tracking.log'
    INPUT_FORMAT = 'oddjob.ManifestTextInputFormat'
    NUM_REDUCERS = 1

    def setUp(self):
        super(AnswerDistributionAcceptanceTest, self).setUp()

        assert 'tasks_output_url' in self.config
        assert 'oddjob_jar' in self.config

        url = self.config['tasks_output_url']
        identifier = self.config.get('identifier', '')

        self.test_root = url_path_join(url, identifier, 'answer_distribution')
        self.test_src = url_path_join(self.test_root, 'src')
        self.test_out = url_path_join(self.test_root, 'out')

        self.oddjob_jar = self.config['oddjob_jar']

        self.s3 = S3Client()

        self.upload_data()

    def upload_data(self):
        src = os.path.join(self.data_dir, 'input', self.INPUT_FILE)
        dst = url_path_join(self.test_src, self.INPUT_FILE)

        # Upload test data file
        self.s3.put(src, dst)

    def test_answer_distribution(self):
        self.launch_task()
        self.validate_output()

    def launch_task(self):
        command = [
            os.getenv('REMOTE_TASK'),
            '--job-flow-name', self.config.get('job_flow_name'),
            '--branch', self.config.get('tasks_branch'),
            '--repo', self.config.get('tasks_repo'),
            '--remote-name', self.config.get('identifier'),
            '--wait',
            '--log-path', self.config.get('tasks_log_path'),
            '--user', self.config.get('connection_user'),
            'AnswerDistributionOneFilePerCourseTask',
            '--local-scheduler',
            '--src',  self.test_src,
            '--dest', url_path_join(self.test_root, 'dst'),
            '--name', 'test',
            '--output-root', self.test_out,
            '--include',  '"*"',
            '--manifest', url_path_join(self.test_root, 'manifest.txt'),
            '--base-input-format', self.INPUT_FORMAT,
            '--lib-jar', self.oddjob_jar,
            '--n-reduce-tasks', str(self.NUM_REDUCERS),
        ]

        self.call_subprocess(command)

    def validate_output(self):
        outputs = self.s3.list(self.test_out)
        outputs = [url_path_join(self.test_out, p) for p in outputs]

        # There are 2 courses in the test data
        self.assertEqual(len(outputs), 2)

        # Check that the results have data
        for output in outputs:
            with S3Target(output).open() as f:
                lines = [l for l in f][1:]  # Skip header
                self.assertTrue(len(lines) > 0)

                # Check that at least one of the count columns is non zero
                get_count = lambda line: int(line.split(',')[3])
                self.assertTrue(any(get_count(l) > 0 for l in lines ))
