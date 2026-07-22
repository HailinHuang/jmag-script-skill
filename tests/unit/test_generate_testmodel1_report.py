import unittest

from jmag_user_py.generate_testmodel1_report import _parse_case_values


class GenerateTestModel1ReportTests(unittest.TestCase):
    def test_preserves_duplicate_jmag_response_column_names(self):
        values = _parse_case_values(
            [["Case", "PM_Loss", "PM_Loss"], ["Case1", "0", "50"]]
        )

        self.assertEqual(values["PM_Loss"], ["0", "50"])


if __name__ == "__main__":
    unittest.main()
