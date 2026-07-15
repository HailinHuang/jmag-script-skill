import unittest
import sys
import types
from unittest.mock import patch

from jmag_functions import (
    JMAGContext,
    get_value,
    get_values,
    run_cases,
    set_parameter,
    set_parameters,
)


class FakeEquation:
    def __init__(self, values):
        self.values = values

    def GetValue(self, index):
        return self.values[index]


class FakeTable:
    def __init__(self, cases=3):
        self.cases = cases
        self.names = ["Equation parameters: speed", "Other: ignored"]
        self.types = ["Equation", "Text"]
        self.equations = {"speed": FakeEquation([1000, 2000, 3000])}
        self.writes = []

    def NumCases(self): return self.cases
    def NumParameters(self): return len(self.names)
    def ParameterName(self, index): return self.names[index]
    def ParameterTypeName(self, index): return self.types[index]
    def GetEquation(self, name): return self.equations[name]
    def SetValue(self, case, parameter, value): self.writes.append((case, parameter, value))


class FakeStudy:
    def __init__(self):
        self.table = FakeTable()
        self.responses = {("torque", 0): [42.0], ("torque", 1): [43.0]}
        self.current = 1
        self.run_all = 0
        self.runs = []

    def GetDesignTable(self): return self.table
    def GetResponseData(self, name, case): return self.responses.get((name, case), [])
    def GetCurrentCase(self): return self.current
    def SetCurrentCase(self, case): self.current = case
    def Run(self): self.runs.append(self.current)
    def RunAllCases(self): self.run_all += 1


class FakeModel:
    def __init__(self, study): self.study = study
    def GetStudy(self, selector): return self.study if selector in (0, "main") else None


class FakeApp:
    def __init__(self):
        self.study = FakeStudy()
        self.model = FakeModel(self.study)
        self.activations = []
        self.quit_count = 0

    def GetCurrentModel(self): return self.model
    def GetCurrentStudy(self): return self.study
    def SetStudyAsCurrent(self, study): self.activations.append(study)
    def Quit(self): self.quit_count += 1


class FunctionTests(unittest.TestCase):
    def setUp(self):
        self.app = FakeApp()
        self.context = JMAGContext.from_current(self.app)

    def test_reads_equation_and_response_with_one_based_cases(self):
        self.assertEqual(get_value(self.context, "speed", case=1), 1000)
        self.assertEqual(get_value(self.context, "torque", case=2), 43.0)
        self.assertEqual(get_values(self.context, ["speed", "torque"], case=1),
                         {"speed": 1000, "torque": 42.0})

    def test_missing_response_and_invalid_cases_fail_clearly(self):
        with self.assertRaises(KeyError): get_value(self.context, "missing")
        for bad in (True, 1.5):
            with self.assertRaises(TypeError): get_value(self.context, "speed", bad)
        for bad in (0, -1, 4):
            with self.assertRaises(ValueError): get_value(self.context, "speed", bad)

    def test_set_parameters_prevalidates_and_never_deletes_results(self):
        set_parameter(self.context, "speed", 2500, case=2)
        self.assertEqual(self.app.study.table.writes, [(1, 0, 2500)])
        with self.assertRaises(KeyError):
            set_parameters(self.context, {"speed": 1, "missing": 2})
        self.assertEqual(self.app.study.table.writes, [(1, 0, 2500)])

    def test_run_subset_and_restore_current_case(self):
        run_cases(self.context, [1, 3])
        self.assertEqual(self.app.study.runs, [0, 2])
        self.assertEqual(self.app.study.current, 1)
        self.assertEqual(self.app.study.run_all, 0)
        run_cases(self.context)
        self.assertEqual(self.app.study.run_all, 1)

    def test_borrowed_context_never_quits(self):
        self.context.close()
        self.context.close()
        self.assertEqual(self.app.quit_count, 0)

    def test_owned_context_quits_once_and_failed_create_does_not_leak(self):
        created = FakeApp()
        designer_api = types.SimpleNamespace(CreateApplication=lambda options: created)
        module = types.SimpleNamespace(designer=designer_api)
        with patch.dict(sys.modules, {"jmag": types.ModuleType("jmag"), "jmag.designer": module}):
            context = JMAGContext.create()
            context.close(); context.close()
        self.assertEqual(created.quit_count, 1)

        broken = FakeApp(); broken.model = None
        designer_api = types.SimpleNamespace(CreateApplication=lambda options: broken)
        module = types.SimpleNamespace(designer=designer_api)
        with patch.dict(sys.modules, {"jmag": types.ModuleType("jmag"), "jmag.designer": module}):
            with self.assertRaises(RuntimeError): JMAGContext.create()
        self.assertEqual(broken.quit_count, 1)

    def test_rejects_ambiguous_collections(self):
        with self.assertRaises(TypeError): get_values(self.context, "speed")
        with self.assertRaises(ValueError): get_values(self.context, ["speed", "speed"])
        with self.assertRaises(ValueError): run_cases(self.context, [])
        with self.assertRaises(ValueError): run_cases(self.context, [1, 1])


if __name__ == "__main__":
    unittest.main()
