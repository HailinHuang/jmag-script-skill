import unittest

from jmag_user_py.testmodel1_function_test import calculate_div_for_intervals


class TestModel1FunctionTestTests(unittest.TestCase):
    def test_calculates_div_without_changing_the_step_equation(self):
        self.assertEqual(calculate_div_for_intervals(12, div_period=1), 8)

    def test_rejects_a_target_that_cannot_preserve_the_existing_formula(self):
        with self.assertRaises(ValueError):
            calculate_div_for_intervals(10, div_period=1)


if __name__ == "__main__":
    unittest.main()
