"""
Tests for tasks that calculate answer distributions.

"""
import json
import StringIO

from edx.analytics.tasks.answer_dist import (
    LastProblemCheckEventMixin,
    AnswerDistributionPerCourseMixin,
)
from edx.analytics.tasks.tests import unittest


class LastProblemCheckEventBaseTest(unittest.TestCase):
    """Base test class for testing LastProblemCheckEventMixin."""

    def setUp(self):
        self.task = LastProblemCheckEventMixin()
        self.course_id = "MITx/7.00x/2013_Spring"
        self.org_id = self.course_id.split('/')[0]
        self.problem_id = "i4x://MITx/7.00x/2013_Spring/problem/PSet1:PS1_Q1"
        self.answer_id = "i4x-MITx-7_00x-problem-PSet1_PS1_Q1_2_1"
        self.username = 'test_user'
        self.user_id = 24
        self.timestamp = "2013-12-17T15:38:32.805444"
        self.key = (self.course_id, self.problem_id, self.username)

    def _create_event_log_line(self, **kwargs):
        """Create an event log with test values, as a JSON string."""
        return json.dumps(self._create_event_dict(**kwargs))

    def _create_event_data_dict(self, **kwargs):
        event_data = {
            "problem_id": self.problem_id,
            "seed": 1,
            "attempts": 2,
            "answers": {self.answer_id: "3"},
            "correct_map": {
                self.answer_id: {
                    "queuestate": None,
                    "npoints": None,
                    "msg": "",
                    "correctness": "incorrect",
                    "hintmode": None,
                    "hint": ""
                },
            },
            "state": {
                "input_state": {self.answer_id: None},
                "correct_map": None,
                "done": False,
                "seed": 1,
                "student_answers": {self.answer_id: "1"},
            },
            "grade": 0,
            "max_grade": 1,
            "success": "incorrect",
        }
        self._update_with_kwargs(event_data, **kwargs)

        return event_data

    @staticmethod
    def _update_with_kwargs(data_dict, **kwargs):
        # Update from kwargs only if it modifies a top-level value.
        for key, value in kwargs.iteritems():
            if key in data_dict:
                data_dict[key] = value

    def _create_event_context(self, **kwargs):
        context = {
            "course_id": self.course_id,
            "org_id": self.org_id,
            "user_id": self.user_id,
        }
        self._update_with_kwargs(context, **kwargs)
        return context

    def _create_problem_data_dict(self, **kwargs):
        problem_data = self._create_event_data_dict(**kwargs)
        problem_data['timestamp'] = self.timestamp
        problem_data['username'] = self.username
        problem_data['context'] = self._create_event_context(**kwargs)

        self._update_with_kwargs(problem_data, **kwargs)
        return problem_data

    def _create_event_dict(self, **kwargs):
        """Create an event log with test values, as a dict."""
        # Define default values for event log entry.
        event_dict = {
            "username": self.username,
            "host": "test_host",
            "event_source": "server",
            "event_type": "problem_check",
            "context": self._create_event_context(**kwargs),
            "time": "{0}+00:00".format(self.timestamp),
            "ip": "127.0.0.1",
            "event": self._create_event_data_dict(**kwargs),
            "agent": "blah, blah, blah",
            "page": None
        }
        self._update_with_kwargs(event_dict, **kwargs)
        return event_dict


class LastProblemCheckEventMapTest(LastProblemCheckEventBaseTest):
    """Tests to verify that event log parsing by mapper works correctly."""

    def assert_no_output_for(self, line):
        """Assert that an input line generates no output."""
        self.assertEquals(tuple(self.task.mapper(line)), tuple())

    def test_non_problem_check_event(self):
        line = 'this is garbage'
        self.assert_no_output_for(line)

    def test_unparseable_problem_check_event(self):
        line = 'this is garbage but contains problem_check'
        self.assert_no_output_for(line)

    def test_browser_event_source(self):
        line = self._create_event_log_line(event_source='browser')
        self.assert_no_output_for(line)

    def test_missing_event_source(self):
        line = self._create_event_log_line(event_source=None)
        self.assert_no_output_for(line)

    def test_missing_username(self):
        line = self._create_event_log_line(username=None)
        self.assert_no_output_for(line)

    def test_missing_event_type(self):
        event_dict = self._create_event_dict()
        event_dict['old_event_type'] = event_dict['event_type']
        del event_dict['event_type']
        line = json.dumps(event_dict)
        self.assert_no_output_for(line)

    def test_implicit_problem_check_event_type(self):
        line = self._create_event_log_line(event_type='implicit/event/ending/with/problem_check')
        self.assert_no_output_for(line)

    def test_bad_datetime(self):
        line = self._create_event_log_line(time='this is a bogus time')
        self.assert_no_output_for(line)

    def test_bad_event_data(self):
        line = self._create_event_log_line(event=["not an event"])
        self.assert_no_output_for(line)

    def test_missing_course_id(self):
        line = self._create_event_log_line(context={})
        self.assert_no_output_for(line)

    def test_illegal_course_id(self):
        line = self._create_event_log_line(course_id=";;;;bad/id/val")
        self.assert_no_output_for(line)

    def test_missing_problem_id(self):
        line = self._create_event_log_line(problem_id=None)
        self.assert_no_output_for(line)

    def test_missing_context(self):
        line = self._create_event_log_line(context=None)
        self.assert_no_output_for(line)

    def test_good_problem_check_event(self):
        event = self._create_event_dict()
        line = json.dumps(event)
        mapper_output = tuple(self.task.mapper(line))
        expected_data = self._create_problem_data_dict()
        expected_key = self.key
        self.assertEquals(len(mapper_output), 1)
        self.assertEquals(len(mapper_output[0]), 2)
        self.assertEquals(mapper_output[0][0], expected_key)
        self.assertEquals(len(mapper_output[0][1]), 2)
        self.assertEquals(mapper_output[0][1][0], self.timestamp)
        # apparently the output of json.dumps() is not consistent enough
        # to compare, due to ordering issues.  So compare the dicts
        # rather than the JSON strings.
        actual_info = mapper_output[0][1][1]
        actual_data = json.loads(actual_info)
        self.assertEquals(actual_data, expected_data)


class LastProblemCheckEventReduceTest(LastProblemCheckEventBaseTest):
    """
    Verify that LastProblemCheckEventMixin.reduce() works correctly.
    """

    def _get_reducer_output(self, values):
        """Run reducer with provided values hardcoded key."""
        return tuple(self.task.reducer(self.key, values))

    def _check_output(self, inputs, expected):
        """Compare generated with expected output."""
        reducer_output = self._get_reducer_output(inputs)
        self.assertEquals(len(reducer_output), len(expected))
        for i, reducer_value in enumerate(reducer_output):
            expected_value = expected[i]
            self.assertEquals(len(reducer_value), 2)
            self.assertEquals(reducer_value[0], expected_value[0])
            self.assertEquals(len(reducer_value[1]), 2)
            self.assertEquals(reducer_value[1][0], self.timestamp)
            # apparently the output of json.dumps() is not consistent enough
            # to compare, due to ordering issues.  So compare the dicts
            # rather than the JSON strings.
            actual_info = reducer_value[1][1]
            actual_data = json.loads(actual_info)
            expected_data = expected_value[1][1]
            self.assertEquals(actual_data, expected_data)

    def test_no_events(self):
        self._check_output([], tuple())

    def test_one_answer_event(self):
        problem_data = self._create_problem_data_dict()
        input_data = (self.timestamp, json.dumps(problem_data))

        answer_data = {
            "answer_value_id": "3",
            "problem_display_name": None,
            "variant": 1,
            "correct": "incorrect",
            "problem_id": self.problem_id,
        }
        expected_key = (self.course_id, self.answer_id)
        expected_value = (self.timestamp, answer_data)

        self._check_output([input_data], [(expected_key, expected_value)])

    def test_one_submission_event(self):
        problem_data = self._create_problem_data_dict()
        problem_data['submission'] = {
            self.answer_id: {
                "input_type": "formulaequationinput",
                "question": "Enter the number of fingers on a human hand",
                "response_type": "numericalresponse",
                "answer": "3",
                "variant": 629,
                "correct": False
            },
        }
        input_data = (self.timestamp, json.dumps(problem_data))
        answer_data = {
            u"answer": u"3",
            u"problem_display_name": None,
            u"variant": 629,
            u"correct": False,
            u"problem_id": unicode(self.problem_id),
            u"input_type": u"formulaequationinput",
            u"question": u"Enter the number of fingers on a human hand",
            u"response_type": u"numericalresponse",
        }
        expected_key = (self.course_id, self.answer_id)
        expected_value = (self.timestamp, answer_data)

        self._check_output([input_data], [(expected_key, expected_value)])

        # TODO: test adding problem_display_name to context.
        # TODO: test with multiple answers from the same problem.
        # TODO: add hidden Ids
        # TODO: add submissions with answer_value_ids.
        # TODO: test multiple answers from the same user (w/different times).
        #     (and different orders).


class AnswerDistributionPerCourseReduceTest(unittest.TestCase):
    """
    Verify that AnswerDistributionPerCourseMixin.reduce() works correctly.
    """
    def setUp(self):
        self.task = AnswerDistributionPerCourseMixin()
        self.course_id = "MITx/7.00x/2013_Spring"
        self.problem_id = "i4x://MITx/7.00x/2013_Spring/problem/PSet1:PS1_Q1"
        self.answer_id = "i4x-MITx-7_00x-problem-PSet1_PS1_Q1_2_1"
        self.timestamp = "2013-12-17T15:38:32.805444"
        self.earlier_timestamp = "2013-12-15T15:38:32.805444"
        self.key = (self.course_id, self.answer_id)
        self.problem_display_name = "This is the Problem for You!"

    def _get_reducer_output(self, values):
        """Run reducer with provided values hardcoded key."""
        return tuple(self.task.reducer(self.key, values))

    def _check_output(self, inputs, expected):
        """Compare generated with expected output."""
        reducer_output = self._get_reducer_output(inputs)
        self.assertEquals(len(reducer_output), len(expected))
        for course_id, _output in reducer_output:
            self.assertEquals(course_id, self.course_id)
        # We don't know what order the outputs will be dumped for a given
        # set of inputs, so we have to compare sets.
        reducer_outputs = set([frozenset(json.loads(output).items()) for _, output in reducer_output])
        expected_outputs = set([frozenset(output.items()) for output in expected])
        self.assertEquals(reducer_outputs, expected_outputs)

    def _get_answer_data(self, **kwargs):
        answer_data = {
            "answer": "3",
            "problem_display_name": None,
            "variant": None,
            "correct": False,
            "problem_id": self.problem_id,
            "input_type": "formulaequationinput",
            "question": "Enter the number of fingers on a human hand",
            "response_type": "numericalresponse",
        }
        answer_data.update(**kwargs)
        return answer_data

    def _get_non_submission_answer_data(self, **kwargs):
        answer_data = {
            "answer_value_id": "3",
            "problem_display_name": None,
            "variant": None,
            "correct": False,
            "problem_id": self.problem_id,
        }
        answer_data.update(**kwargs)
        return answer_data

    def _get_expected_output(self, answer_data, **kwargs):
        """Get an output based on the input."""
        expected_output = {
            "Problem Display Name": answer_data.get('problem_display_name'),
            "Count": 1,
            "PartID": self.answer_id,
            "Question": answer_data.get('question'),
            "AnswerValue": answer_data.get('answer'),
            "ValueID": "",
            "Variant": answer_data.get('variant'),
            "Correct Answer": "1" if answer_data['correct'] else '0',
            "ModuleID": self.problem_id,
        }
        expected_output.update(**kwargs)
        return expected_output

    def test_no_user_counts(self):
        self.assertEquals(self._get_reducer_output([]), tuple())

    def test_one_answer_event(self):
        answer_data = self._get_answer_data()
        input_data = (self.timestamp, json.dumps(answer_data))
        expected_output = self._get_expected_output(answer_data)
        self._check_output([input_data], (expected_output,))

    def test_event_with_variant(self):
        answer_data = self._get_answer_data(variant=629)
        input_data = (self.timestamp, json.dumps(answer_data))
        expected_output = self._get_expected_output(answer_data)
        self._check_output([input_data], (expected_output,))

    def test_event_with_problem_name(self):
        answer_data = self._get_answer_data(problem_display_name=self.problem_display_name)
        input_data = (self.timestamp, json.dumps(answer_data))
        expected_output = self._get_expected_output(answer_data)
        self._check_output([input_data], (expected_output,))

    def test_choice_answer(self):
        answer_data = self._get_answer_data(
            answer_value_id='choice_1',
            answer='First Choice',
        )
        input_data = (self.timestamp, json.dumps(answer_data))
        expected_output = self._get_expected_output(answer_data,
            ValueID='choice_1',
            AnswerValue='First Choice'
        )
        self._check_output([input_data], (expected_output,))

    def test_multiple_choice_answer(self):
        answer_data = self._get_answer_data(
            answer_value_id=['choice_1','choice_2','choice_4'],
            answer=['First Choice','Second Choice','Fourth Choice'],
            response_type="multiplechoiceresponse",
        )
        input_data = (self.timestamp, json.dumps(answer_data))
        expected_output = self._get_expected_output(answer_data,
            ValueID='[choice_1|choice_2|choice_4]',
            AnswerValue='[First Choice|Second Choice|Fourth Choice]'
        )
        self._check_output([input_data], (expected_output,))

    def test_filtered_response_type(self):
        answer_data = self._get_answer_data(
            response_type="customresponse",
        )
        input_data = (self.timestamp, json.dumps(answer_data))
        self.assertEquals(self._get_reducer_output([input_data]), tuple())

    def test_filtered_non_submission_answer(self):
        answer_data = self._get_non_submission_answer_data()
        input_data = (self.timestamp, json.dumps(answer_data))
        self.assertEquals(self._get_reducer_output([input_data]), tuple())

    def test_two_answer_event_same(self):
        answer_data = self._get_answer_data()
        input_data_1 = (self.earlier_timestamp, json.dumps(answer_data))
        input_data_2 = (self.timestamp, json.dumps(answer_data))
        expected_output = self._get_expected_output(answer_data, Count=2)
        self._check_output([input_data_1, input_data_2], (expected_output,))

    def test_two_answer_event_same_reversed(self):
        answer_data = self._get_answer_data()
        input_data_1 = (self.earlier_timestamp, json.dumps(answer_data))
        input_data_2 = (self.timestamp, json.dumps(answer_data))
        expected_output = self._get_expected_output(answer_data, Count=2)
        self._check_output([input_data_2, input_data_1], (expected_output,))

    def test_two_answer_event_same_old_and_new(self):
        answer_data_1 = self._get_non_submission_answer_data()
        answer_data_2 = self._get_answer_data()
        input_data_1 = (self.earlier_timestamp, json.dumps(answer_data_1))
        input_data_2 = (self.timestamp, json.dumps(answer_data_2))
        expected_output = self._get_expected_output(answer_data_2, Count=2)
        self._check_output([input_data_1, input_data_2], (expected_output,))

    def test_two_answer_event_different_answer(self):
        answer_data_1 = self._get_answer_data(answer="first")
        answer_data_2 = self._get_answer_data(answer="second")
        input_data_1 = (self.earlier_timestamp, json.dumps(answer_data_1))
        input_data_2 = (self.timestamp, json.dumps(answer_data_2))
        expected_output_1 = self._get_expected_output(answer_data_1)
        expected_output_2 = self._get_expected_output(answer_data_2)
        self._check_output([input_data_1, input_data_2], (expected_output_1, expected_output_2))

    def test_two_answer_event_different_variant(self):
        answer_data_1 = self._get_answer_data(variant=123)
        answer_data_2 = self._get_answer_data(variant=456)
        input_data_1 = (self.earlier_timestamp, json.dumps(answer_data_1))
        input_data_2 = (self.timestamp, json.dumps(answer_data_2))
        expected_output_1 = self._get_expected_output(answer_data_1)
        expected_output_2 = self._get_expected_output(answer_data_2)
        self._check_output([input_data_1, input_data_2], (expected_output_1, expected_output_2))

    def _load_metadata(self, **kwargs):
        """Defines some metadata for test answer."""
        metadata_dict = { 
            self.answer_id: { 
                "question": "Pick One or Two",
                "response_type": "multiplechoiceresponse",
                "input_type": "my_input_type",
                "problem_display_name": self.problem_display_name,
            }
        }
        metadata_dict[self.answer_id].update(**kwargs)
        answer_metadata = StringIO.StringIO(json.dumps(metadata_dict))
        self.task.load_answer_metadata(answer_metadata)

    def test_non_submission_choice_with_metadata(self):
        self._load_metadata(
            answer_value_id_map={"choice_1": "First Choice", "choice_2": "Second Choice"}
        )
        answer_data = self._get_non_submission_answer_data(
            answer_value_id='choice_1',
        )
        input_data = (self.timestamp, json.dumps(answer_data))
        expected_output = self._get_expected_output(answer_data,
            ValueID='choice_1',
            AnswerValue='First Choice',
            Question="Pick One or Two",
        )
        expected_output["Problem Display Name"] = self.problem_display_name
        self._check_output([input_data], (expected_output,))

    def test_non_submission_multichoice_with_metadata(self):
        self._load_metadata(
            answer_value_id_map={"choice_1": "First Choice", "choice_2": "Second Choice"}
        )
        answer_data = self._get_non_submission_answer_data(
            answer_value_id=['choice_1','choice_2']
        )
        input_data = (self.timestamp, json.dumps(answer_data))
        expected_output = self._get_expected_output(answer_data,
            ValueID='[choice_1|choice_2]',
            AnswerValue='[First Choice|Second Choice]',
            Question="Pick One or Two",
        )
        expected_output["Problem Display Name"] = self.problem_display_name

        self._check_output([input_data], (expected_output,))

    def test_non_submission_nonmapped_multichoice_with_metadata(self):
        self._load_metadata()
        answer_data = self._get_non_submission_answer_data(
            answer_value_id=['choice_1','choice_2']
        )
        input_data = (self.timestamp, json.dumps(answer_data))
        expected_output = self._get_expected_output(answer_data,
            ValueID='[choice_1|choice_2]',
            AnswerValue='',
            Question="Pick One or Two",
        )
        expected_output["Problem Display Name"] = self.problem_display_name
        self._check_output([input_data], (expected_output,))

    def test_non_submission_nonmapped_choice_with_metadata(self):
        self._load_metadata()
        answer_data = self._get_non_submission_answer_data(
            answer_value_id='choice_1'
        )
        input_data = (self.timestamp, json.dumps(answer_data))
        expected_output = self._get_expected_output(answer_data,
            ValueID='choice_1',
            AnswerValue='',
            Question="Pick One or Two",
        )
        expected_output["Problem Display Name"] = self.problem_display_name
        self._check_output([input_data], (expected_output,))

    def test_non_submission_nonmapped_nonchoice_with_metadata(self):
        self._load_metadata(response_type="optionresponse")
        answer_data = self._get_non_submission_answer_data()
        input_data = (self.timestamp, json.dumps(answer_data))
        expected_output = self._get_expected_output(answer_data,
            AnswerValue='3',
            Question="Pick One or Two",
        )
        expected_output["Problem Display Name"] = self.problem_display_name
        self._check_output([input_data], (expected_output,))
