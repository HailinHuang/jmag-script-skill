import unittest

from jmag_functions import JMAGContext
from jmag_functions.orchestration import evaluate_cases
from tests.unit.test_functions import FakeApp


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.app = FakeApp()
        self.context = JMAGContext.from_current(self.app)

    def test_sets_runs_and_reads_only_requested_one_based_cases(self):
        result = evaluate_cases(
            self.context,
            {"speed": 2500},
            ["speed", "torque"],
            [1, 2],
            clear_results=True,
        )

        self.assertEqual(
            result,
            {
                1: {"speed": 2500, "torque": 42.0},
                2: {"speed": 2500, "torque": 43.0},
            },
        )
        self.assertEqual(self.app.study.runs, [0, 1])
        self.assertEqual(self.app.study.deleted, 1)
        self.assertEqual(self.app.study.applied, 1)
        self.assertEqual(self.app.study.current, 1)

    def test_prevalidation_prevents_partial_writes_or_runs(self):
        with self.assertRaises(KeyError):
            evaluate_cases(
                self.context,
                {"speed": 2500, "missing": 1},
                ["torque"],
                1,
                clear_results=True,
            )
        self.assertEqual(self.app.study.table.writes, [])
        self.assertEqual(self.app.study.runs, [])
        self.assertEqual(self.app.study.deleted, 0)

    def test_rejects_ambiguous_case_and_name_collections(self):
        with self.assertRaises(TypeError):
            evaluate_cases(
                self.context,
                {"speed": 2500},
                "torque",
                1,
                clear_results=False,
            )
        with self.assertRaises(ValueError):
            evaluate_cases(
                self.context,
                {"speed": 2500},
                ["torque"],
                [1, 1],
                clear_results=False,
            )

    def test_requires_boolean_result_clearing_policy(self):
        with self.assertRaises(TypeError):
            evaluate_cases(
                self.context,
                {"speed": 2500},
                ["torque"],
                1,
                clear_results="yes",
            )


if __name__ == "__main__":
    unittest.main()
