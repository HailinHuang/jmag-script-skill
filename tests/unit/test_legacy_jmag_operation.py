import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[2] / "jmag_user_py" / "users" / "jmag_operation.py"


class FakeEquation:
    def __init__(self, values):
        self.values = values

    def GetValue(self, index):
        return self.values[index]


class FakeTable:
    def __init__(self):
        self.names = ["Equation parameters: speed", "Equation parameters: angle"]
        self.types = ["Equation", "Equation"]
        self.equations = {
            "speed": FakeEquation([1000, 2000, 3000]),
            "angle": FakeEquation([10, 20, 30]),
        }
        self.writes = []

    def NumCases(self):
        return 3

    def NumParameters(self):
        return len(self.names)

    def ParameterName(self, index):
        return self.names[index]

    def ParameterTypeName(self, index):
        return self.types[index]

    def GetEquation(self, name):
        return self.equations[name]

    def SetValue(self, case_index, parameter_index, value):
        self.writes.append((case_index, parameter_index, value))
        name = self.names[parameter_index].removeprefix("Equation parameters: ")
        self.equations[name].values[case_index] = value


class FakeReport:
    def HasWarningMessage(self):
        return False


class FakeStudy:
    def __init__(self):
        self.table = FakeTable()
        self.responses = {("torque", 0): [42.0], ("torque", 1): [43.0]}
        self.current_case = 1
        self.deleted = 0
        self.applied = 0
        self.runs = []

    def GetDesignTable(self):
        return self.table

    def GetResponseData(self, name, case_index):
        return self.responses.get((name, case_index), [])

    def GetReport(self):
        return FakeReport()

    def DeleteResult(self):
        self.deleted += 1
        self.responses.clear()

    def ApplyCadParameters(self):
        self.applied += 1

    def ApplyAllCasesCadParameters(self):
        self.applied += 1

    def GetCurrentCase(self):
        return self.current_case

    def SetCurrentCase(self, case_index):
        self.current_case = case_index

    def Run(self):
        self.runs.append(self.current_case)
        self.responses[("torque", self.current_case)] = [100.0 + self.current_case]


class FakeModel:
    def __init__(self, study):
        self.study = study

    def GetStudy(self, selector):
        return self.study if selector in (0, "main") else None


class FakeApp:
    def __init__(self):
        self.study = FakeStudy()
        self.model = FakeModel(self.study)
        self.get_application_calls = 0

    def GetCurrentModel(self):
        return self.model

    def GetCurrentStudy(self):
        return self.study

    def GetCurrentResult(self):
        return None

    def SetCurrentStudy(self, selector):
        if selector not in (0, "main"):
            raise KeyError(selector)

    def GetStudy(self, selector):
        return self.model.GetStudy(selector)

    def GetModel(self, selector):
        return self.model if selector == 0 else None


def load_module(app):
    designer_api = types.SimpleNamespace(GetApplication=lambda: app)
    designer_module = types.ModuleType("jmag.designer")
    designer_module.designer = designer_api
    stubs = {
        "jmag": types.ModuleType("jmag"),
        "jmag.designer": designer_module,
        "end_winding_calc": types.ModuleType("end_winding_calc"),
        "csv_operation": types.ModuleType("csv_operation"),
        "numpy": types.ModuleType("numpy"),
        "scipy": types.ModuleType("scipy"),
    }
    stubs["scipy"].interpolate = types.SimpleNamespace()
    spec = importlib.util.spec_from_file_location("legacy_jmag_operation", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


class LegacyJmagOperationTests(unittest.TestCase):
    def setUp(self):
        self.app = FakeApp()
        self.module = load_module(self.app)

    def test_initialization_does_not_refresh_only_because_result_is_missing(self):
        calls = 0

        def get_application():
            nonlocal calls
            calls += 1
            return self.app

        self.module.designer.GetApplication = get_application
        first = self.module.initialize_jmag()
        second = self.module.initialize_jmag()
        self.assertIsNone(first[3])
        self.assertEqual(first, second)
        self.assertEqual(calls, 1)

    def test_get_data_uses_one_based_cases_and_get_datas_treats_string_as_one_name(self):
        self.assertEqual(self.module.get_data("speed", "main", 2), 2000)
        self.assertEqual(self.module.get_data("torque", "main", [1, 2]), 85.0)
        self.assertEqual(self.module.get_datas("speed", "main", 1), [1000])
        with self.assertRaises(KeyError):
            self.module.get_data("missing", "main", 1)
        with self.assertRaises(ValueError):
            self.module.get_data("speed", "main", 0)

    def test_set_paras_prevalidates_and_deletes_results_once(self):
        result = self.module.set_paras(
            ["speed", "angle"], [2500, 25], "main", [1, 2]
        )
        self.assertIsNone(result)
        self.assertEqual(
            self.app.study.table.writes,
            [(0, 0, "2500"), (0, 1, "25"), (1, 0, "2500"), (1, 1, "25")],
        )
        self.assertEqual(self.app.study.deleted, 1)
        self.assertEqual(self.app.study.applied, 1)

        self.module.set_paras(["speed", "angle"], ["2500", "25"], "main", [1, 2])
        self.assertEqual(len(self.app.study.table.writes), 4)
        self.assertEqual(self.app.study.deleted, 1)

        before = list(self.app.study.table.writes)
        deleted_before = self.app.study.deleted
        with self.assertRaises(KeyError):
            self.module.set_paras(["speed", "missing"], [1, 2], "main", 1)
        self.assertEqual(self.app.study.table.writes, before)
        self.assertEqual(self.app.study.deleted, deleted_before)

        with self.assertRaises(ValueError):
            self.module.set_paras(["speed", "angle"], [1], "main", 1)
        with self.assertRaises(ValueError):
            self.module.set_paras(["speed", "speed"], [1, 2], "main", 1)

    def test_leave_result_and_selected_case_execution_are_explicit(self):
        self.module.set_para_leave_result("speed", 2500, "main", 2)
        self.assertEqual(self.app.study.deleted, 0)
        self.assertEqual(self.app.study.table.writes, [(1, 0, "2500")])

        self.module.run_case("main", [1, 3], clear_results=True)
        self.assertEqual(self.app.study.runs, [0, 2])
        self.assertEqual(self.app.study.current_case, 1)
        self.assertEqual(self.app.study.deleted, 1)

    def test_invalid_cases_fail_before_result_deletion_or_execution(self):
        for case in (True, 0, 4, [], [1, 1]):
            with self.subTest(case=case):
                with self.assertRaises((TypeError, ValueError)):
                    self.module.run_case("main", case)
        self.assertEqual(self.app.study.deleted, 0)
        self.assertEqual(self.app.study.runs, [])

    def test_set_run_read_orchestration_runs_only_requested_case_once(self):
        values = self.module.get_datas_set_paras(
            "torque", "speed", 2500, "main", 2
        )
        self.assertEqual(values, [101.0])
        self.assertEqual(self.app.study.deleted, 1)
        self.assertEqual(self.app.study.runs, [1])
        self.assertEqual(self.app.study.current_case, 1)


if __name__ == "__main__":
    unittest.main()
