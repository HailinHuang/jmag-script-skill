import sys
import json
import tomllib
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from jmag_functions import JMAGContext
from jmag_functions.exports import (
    export_case_values,
    export_design_table,
    export_result_tables,
)
from jmag_functions.inventory import (
    export_inventory_html,
    inventory_design_table,
    render_inventory_html,
)
from jmag_functions.project import (
    close_application,
    create_application,
    launch_project_in_visible_designer,
    load_project,
    load_project_copy,
    open_project,
    open_project_visible,
    ProjectSession,
    select_study,
    save_project,
    save_project_as,
    open_jmag_fast,
)

from jmag_functions import __version__ as function_version
from jmag_skill import __version__ as skill_version
from jmag_skill.cli import __version__ as cli_version


class MetadataEquation:
    def GetValue(self, case): return 12 + case
    def GetName(self): return "steps"
    def GetDisplayName(self): return "Steps"
    def GetDescription(self): return "Transient steps"
    def GetExpression(self): return "Div + 1"


class ResultTable:
    def __init__(self, events): self.events = events
    def WriteAllCaseTables(self, path, axis):
        self.events.append(("result_tables", path, axis))


class Table:
    def __init__(self, events): self.events = events
    def NumCases(self): return 1
    def NumParameters(self): return 2
    def ParameterName(self, index):
        return ["Equation parameters: steps", "Study Properties: Step"][index]
    def ParameterTypeName(self, index): return ["Equation", "Flag"][index]
    def GetValue(self, case, index): return ["Div + 1", 13][index]
    def GetEquation(self, name): return MetadataEquation()
    def Export(self, path): self.events.append(("design_table", path))


class BrokenEquationTable(Table):
    def NumParameters(self): return 3
    def ParameterName(self, index):
        return [
            "Equation parameters: steps",
            "Equation parameters: ",
            "Equation parameters: broken",
        ][index]
    def ParameterTypeName(self, index): return "Equation"
    def GetValue(self, case, index): return ["Div + 1", "", "missing"][index]
    def GetEquation(self, name):
        if name == "broken":
            raise KeyError("")
        return MetadataEquation()


class RelationEquation:
    def __init__(self, name, expression, value):
        self.name = name
        self.expression = expression
        self.value = value
    def GetValue(self, case): return self.value
    def GetName(self): return self.name
    def GetDisplayName(self): return self.name
    def GetDescription(self): return ""
    def GetExpression(self): return self.expression


class RelationshipTable(Table):
    names = [
        "Equation parameters: Div",
        "Equation parameters: Step",
        "Study Properties: Step",
    ]
    types = ["Equation", "Equation", "Flag"]
    def NumParameters(self): return len(self.names)
    def ParameterName(self, index): return self.names[index]
    def ParameterTypeName(self, index): return self.types[index]
    def GetValue(self, case, index): return [8, "Div + 1", 13][index]
    def GetEquation(self, name):
        return {
            "Div": RelationEquation("Div", "8", 8),
            "Step": RelationEquation("Step", "Div + 1", 13),
        }[name]
    def GetRelatedParameterNames(self, name):
        return {"Div": [], "Step": ["Study Properties: Step"]}[name]


class Study:
    def __init__(self, events):
        self.events = events
        self.table = Table(events)
        self.result_table = ResultTable(events)
    def GetDesignTable(self): return self.table
    def ExportCaseValueData(self, path): self.events.append(("case_values", path))
    def GetResultTable(self): return self.result_table


class Model:
    def __init__(self, study): self.study = study
    def GetStudy(self, selector): return self.study


class App:
    def __init__(self):
        self.events = []
        self.study = Study(self.events)
        self.model = Model(self.study)
        self.quit_count = 0
    def GetCurrentModel(self): return self.model
    def GetCurrentStudy(self): return self.study
    def SetStudyAsCurrent(self, study): self.events.append(("activate", study))
    def Load(self, path): self.events.append(("load", path))
    def Save(self): self.events.append(("save",))
    def SaveAs(self, path): self.events.append(("save_as", path))
    def Quit(self): self.quit_count += 1


class ReuseFunctionTests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.context = JMAGContext.from_current(self.app)

    def test_library_catalog_cli_and_skill_versions_match(self):
        catalog = json.loads(
            Path("references/function-catalog.json").read_text(encoding="utf-8")
        )
        pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(
            {
                function_version,
                skill_version,
                cli_version,
                catalog["library_version"],
                pyproject["project"]["version"],
            },
            {"0.3.0"},
        )

    def test_inventory_records_all_parameters_and_equation_metadata(self):
        records = inventory_design_table(
            self.context, case=1, include_equation_metadata=True
        )
        self.assertEqual(records[0]["equation"]["expression"], "Div + 1")
        self.assertEqual(records[0]["equation"]["evaluated_value"], 12)
        self.assertEqual(records[1]["value"], 13)

    def test_inventory_preserves_unnamed_and_broken_equation_entries(self):
        table = BrokenEquationTable(self.app.events)
        self.context.table = table
        self.app.study.table = table
        records = inventory_design_table(
            self.context, case=1, include_equation_metadata=True
        )
        self.assertEqual(records[1]["equation_error"], "Equation parameter has no name")
        self.assertIn("KeyError", records[2]["equation_error"])
        self.assertEqual(len(records), 3)

    def test_inventory_infers_relationships_and_renders_a_visual_table(self):
        table = RelationshipTable(self.app.events)
        self.context.table = table
        self.app.study.table = table
        records = inventory_design_table(self.context, case=1)
        step = records[1]
        self.assertEqual(step["relationships"]["references"], ["Div"])
        self.assertEqual(records[0]["relationships"]["dependents"], ["Step"])
        self.assertEqual(step["inferred_purpose"]["category"], "simulation")
        html = render_inventory_html(records, title="Test Model")
        self.assertIn("Test Model", html)
        self.assertIn("Relationship", html)
        self.assertIn("Step", html)

    def test_inventory_visualization_export_requires_a_safe_html_path(self):
        records = inventory_design_table(self.context, case=1)
        output = Path.cwd() / "inventory.html"
        with patch.object(Path, "write_text") as write_text:
            exported = export_inventory_html(records, output, title="Inventory")
        self.assertEqual(exported, output.resolve())
        self.assertTrue(write_text.called)
        with self.assertRaises(ValueError):
            export_inventory_html(records, Path.cwd() / "inventory.csv")
        with patch.object(Path, "is_dir", return_value=False):
            with self.assertRaises(FileNotFoundError):
                export_inventory_html(records, Path.cwd() / "missing" / "inventory.html")

    def test_exports_are_explicit_and_reject_overwrite_or_bad_axis(self):
        root = Path.cwd()
        export_design_table(self.context, root / "design.csv")
        export_case_values(self.context, root / "cases.csv")
        export_result_tables(self.context, root / "results.csv", axis="Step")
        existing = root / "existing.csv"
        with patch.object(Path, "exists", return_value=True):
            with self.assertRaises(FileExistsError):
                export_design_table(self.context, existing)
            export_design_table(self.context, existing, overwrite=True)
        with self.assertRaises(ValueError):
            export_result_tables(self.context, root / "bad.csv", axis="RPM")
        with self.assertRaises(ValueError):
            export_case_values(self.context, root / "bad.xlsx")
        with patch.object(Path, "is_dir", return_value=False):
            with self.assertRaises(FileNotFoundError):
                export_case_values(self.context, root / "missing" / "cases.csv")
        self.assertIn(("result_tables", str(root / "results.csv"), "Step"), self.app.events)

    def test_load_project_copy_never_overwrites_and_owns_created_app(self):
        designer_api = types.SimpleNamespace(CreateApplication=lambda options: self.app)
        module = types.SimpleNamespace(designer=designer_api)
        source = Path("C:/virtual/source.jproj")
        target = Path("C:/virtual/copy.jproj")
        with (
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "exists", return_value=False),
            patch.object(Path, "is_dir", return_value=True),
        ):
            with patch.dict(
                sys.modules,
                {"jmag": types.ModuleType("jmag"), "jmag.designer": module},
            ):
                project = load_project_copy(source, target)
        self.assertEqual(
            self.app.events[:2],
            [("load", str(source.resolve())), ("save_as", str(target.resolve()))],
        )
        project.close()
        self.assertEqual(self.app.quit_count, 1)
        with (
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "exists", return_value=True),
        ):
            with self.assertRaises(FileExistsError):
                load_project_copy(source, target)

    def test_open_project_visible_loads_selects_study_and_keeps_application_open(self):
        creation_options = []
        designer_api = types.SimpleNamespace(
            CreateApplication=lambda options: creation_options.append(options) or self.app
        )
        module = types.SimpleNamespace(designer=designer_api)
        source = Path("C:/virtual/TestModel1.jproj")
        with (
            patch.object(Path, "is_file", return_value=True),
            patch.dict(
                sys.modules,
                {"jmag": types.ModuleType("jmag"), "jmag.designer": module},
            ),
        ):
            opened = open_project_visible(source, study="Main")
        self.assertIs(opened, self.app)
        self.assertEqual(creation_options, [[]])
        self.assertEqual(self.app.events[:2], [
            ("load", str(source.resolve())),
            ("activate", self.app.study),
        ])
        self.assertEqual(self.app.quit_count, 0)

    def test_launch_project_in_visible_designer_starts_designer_with_project_path(self):
        source = Path("C:/virtual/TestModel1.jproj")
        with patch.object(Path, "is_file", return_value=True), patch(
            "jmag_functions.project.subprocess.Popen"
        ) as popen:
            launched = launch_project_in_visible_designer(source)
        self.assertIs(launched, popen.return_value)
        popen.assert_called_once_with([
            r"C:\Program Files\JMAG-Designer25.1\designer.exe",
            str(source.resolve()),
        ])

    def test_project_lifecycle_functions_create_load_save_and_close_explicitly(self):
        creation_options = []
        designer_api = types.SimpleNamespace(
            CreateApplication=lambda options: creation_options.append(options) or self.app
        )
        module = types.SimpleNamespace(designer=designer_api)
        source = Path("C:/virtual/TestModel1.jproj")
        target = Path("C:/virtual/SavedModel.jproj")
        with (
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "exists", return_value=False),
            patch.object(Path, "is_dir", return_value=True),
            patch.dict(
                sys.modules,
                {"jmag": types.ModuleType("jmag"), "jmag.designer": module},
            ),
        ):
            app = create_application(visible=True)
            self.assertIs(app, self.app)
            self.assertEqual(creation_options, [[]])
            self.assertIs(load_project(app, source, study="Main"), app)
            save_project(app)
            saved = save_project_as(app, target)
            close_application(app, save=True)
        self.assertEqual(saved, target.resolve())
        self.assertEqual(self.app.events, [
            ("load", str(source.resolve())),
            ("activate", self.app.study),
            ("save",),
            ("save_as", str(target.resolve())),
            ("save",),
        ])
        self.assertEqual(self.app.quit_count, 1)

    def test_close_application_does_not_save_by_default(self):
        close_application(self.app)
        self.assertEqual(self.app.events, [])
        self.assertEqual(self.app.quit_count, 1)

    def test_open_project_selects_visible_mode_and_loads_in_one_call(self):
        creation_options = []
        designer_api = types.SimpleNamespace(
            CreateApplication=lambda options: creation_options.append(options) or self.app
        )
        module = types.SimpleNamespace(designer=designer_api)
        source = Path("C:/virtual/TestModel1.jproj")
        with (
            patch.object(Path, "is_file", return_value=True),
            patch.dict(
                sys.modules,
                {"jmag": types.ModuleType("jmag"), "jmag.designer": module},
            ),
        ):
            opened = open_project(source, visible=True, study="Main")
        self.assertIs(opened, self.app)
        self.assertEqual(creation_options, [[]])
        self.assertEqual(self.app.events[:2], [
            ("load", str(source.resolve())),
            ("activate", self.app.study),
        ])

    def test_project_session_context_closes_application(self):
        with patch("jmag_functions.project.open_project", return_value=self.app):
            with ProjectSession.open("C:/virtual/TestModel1.jproj") as project:
                self.assertIs(project.app, self.app)
        self.assertEqual(self.app.quit_count, 1)

    def test_project_copy_closes_owned_app_on_failure(self):
        source = Path("C:/virtual/source.jproj")
        target = Path("C:/virtual/copy.jproj")
        failing = App()
        failing.SaveAs = lambda path: (_ for _ in ()).throw(RuntimeError("save failed"))
        designer_api = types.SimpleNamespace(CreateApplication=lambda options: failing)
        module = types.SimpleNamespace(designer=designer_api)
        with (
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "exists", return_value=False),
            patch.object(Path, "is_dir", return_value=True),
            patch.dict(
                sys.modules,
                {"jmag": types.ModuleType("jmag"), "jmag.designer": module},
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "save failed"):
                load_project_copy(source, target)
        self.assertEqual(failing.quit_count, 1)

    def test_project_copy_validates_source_target_and_parent_before_launch(self):
        source = Path("C:/virtual/source.jproj")
        target = Path("C:/virtual/copy.jproj")
        with patch.object(Path, "is_file", return_value=False):
            with self.assertRaises(FileNotFoundError):
                load_project_copy(source, target)

    def test_open_jmag_fast_original_preflights_and_launches(self):
        source = Path("C:/virtual/source.jproj")
        process = object()
        with (
            patch.object(Path, "is_file", return_value=True),
            patch("jmag_functions.project.find_missing_result_files", return_value=[]),
            patch("jmag_functions.project.launch_project_in_visible_designer", return_value=process) as launch,
        ):
            result = open_jmag_fast(source)
        self.assertIs(result, process)
        launch.assert_called_once_with(
            source.resolve(),
            designer_executable=Path(r"C:\Program Files\JMAG-Designer25.1\designer.exe"),
        )

    def test_open_jmag_fast_copy_preserves_source_and_confirms_missing_dialog(self):
        source = Path("C:/virtual/source.jproj")
        target = Path("C:/virtual/copy.jproj")
        with (
            patch.object(Path, "is_file", return_value=True),
            patch("jmag_functions.project.find_missing_result_files", return_value=["missing.jplot"]),
            patch("jmag_functions.project.dismiss_missing_result_dialog", return_value=True),
            patch("jmag_functions.project.copy_project_bundle", return_value=target) as copy,
            patch("jmag_functions.project.launch_project_in_visible_designer", return_value=object()) as launch,
        ):
            result = open_jmag_fast(source, mode="copy", copy_target=target)
        copy.assert_called_once_with(source.resolve(), target.resolve())
        self.assertEqual(result, launch.return_value)
        with patch.object(Path, "is_file", return_value=True):
            with self.assertRaises(ValueError):
                load_project_copy(source, source)
        with (
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "exists", return_value=False),
            patch.object(Path, "is_dir", return_value=False),
        ):
            with self.assertRaises(FileNotFoundError):
                load_project_copy(source, target)


if __name__ == "__main__":
    unittest.main()
