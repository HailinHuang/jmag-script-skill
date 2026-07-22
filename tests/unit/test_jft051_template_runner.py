from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[2] / "jmag_user_py" / "jft051_geometry_template.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("jft051_runner_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Jft051TemplateRunnerTests(unittest.TestCase):
    def test_configure_runtime_adds_jmag_root_before_application_creation(self):
        runner = _load_runner()
        with patch.object(runner, "JMAG_ROOT", Path("C:/JMAG-Designer25.1")):
            with patch.object(sys, "path", []):
                runner.configure_jmag_runtime()
                self.assertEqual(sys.path, ["C:\\JMAG-Designer25.1"])

    def test_sector_adapter_uses_the_geometry_editor_default_document(self):
        runner = _load_runner()

        class Equation:
            def SetType(self, value): pass
            def SetExpression(self, value): pass
            def SetDescription(self, value): pass
            def SetRegistrationSource(self, value): pass
            def SetRegisterToDesigner(self, value): pass
            def SetIsFactorKey(self, value): pass
            def SetTrueValue(self, value): pass
            def SetFalseValue(self, value): pass
            def SetDisplayName(self, value): pass

        class Table:
            def EditStart(self): pass
            def AddEquation(self, name): pass
            def GetEquation(self, name): return Equation()
            def EditEnd(self): pass

        class Constraint:
            def SetEquation(self, name): pass

        class Selection:
            def Clear(self): pass
            def Add(self, item): pass

        class Sketch:
            def SetName(self, name): pass
            def OpenSketch(self): pass
            def CreateLine(self, *args): return object()
            def CreateArc(self, *args): return object()
            def CreateMonoConstraint(self, *args): return Constraint()
            def CreateRegions(self): pass
            def CloseSketch(self): pass

        class Assembly:
            def GetPlaneXY(self): return object()
            def CreateSketch(self, plane): return Sketch()

        class Document:
            def GetDesignTable(self): return Table()
            def GetAssembly(self): return Assembly()
            def CreateReferenceFromItem(self, item): return object()
            def GetSelection(self): return Selection()
            def UpdateModel(self, *args): pass

        class GeometryEditor:
            def NewDocument(self): raise AssertionError("NewDocument must not be called")
            def GetDocument(self): return Document()

        runner.JmagSectorAdapter(GeometryEditor()).build_sector(
            angle_deg=90.0,
            radius_mm=100.0,
            equation_names={"angle": "Angle", "radius": "Radius"},
        )


if __name__ == "__main__":
    unittest.main()
