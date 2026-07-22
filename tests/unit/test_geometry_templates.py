import json
import tempfile
import unittest
from pathlib import Path

from jmag_functions.geometry_templates import (
    GeometryTemplateSpec,
    GeometryTemplateWorkflow,
    RegistrationStateError,
)
from jmag_functions.geometry_template_ui import UiControlNotFound, register_template_via_ui


class FakeGeometry:
    def __init__(self):
        self.events = []

    def build_sector(self, *, angle_deg, radius_mm, equation_names):
        self.events.append(("build", angle_deg, radius_mm, equation_names))

    def save_as(self, path):
        Path(path).write_text("fake jmdl", encoding="utf-8")
        self.events.append(("save", str(path)))

    def insert_library(self, library_key, rename_map):
        self.events.append(("insert", library_key, rename_map))

    def set_equations(self, values):
        self.events.append(("set_equations", values))

    def read_equations(self, names):
        self.events.append(("read_equations", tuple(names)))
        return {"Angle": 30.0, "Radius": 100.0}


class FakeUi:
    def __init__(self, command=True):
        self.command = command
        self.events = []

    def ensure_editor_visible(self): self.events.append("visible")
    def find_command(self, name):
        self.events.append(("find", name))
        return name if self.command else None
    def invoke(self, control): self.events.append(("invoke", control))
    def wait_for_dialog(self, title): self.events.append(("dialog", title)); return title
    def set_text(self, dialog, field, value): self.events.append(("text", field, value))
    def set_checked(self, dialog, field, value): self.events.append(("check", field, value))
    def confirm(self, dialog): self.events.append(("confirm", dialog))
    def has_library_item(self, key): self.events.append(("has", key)); return True
    def capture(self, label): self.events.append(("capture", label))


class GeometryTemplateWorkflowTests(unittest.TestCase):
    def test_spec_rejects_unsafe_template_id_and_nonpositive_units(self):
        with self.assertRaises(ValueError):
            GeometryTemplateSpec(template_id="bad/name")
        with self.assertRaises(ValueError):
            GeometryTemplateSpec(template_id="template", radius_mm=0.0)
        with self.assertRaises(ValueError):
            GeometryTemplateSpec(template_id="template", insertion_angle_deg=0.0)

    def test_build_creates_new_run_manifest_and_refuses_existing_target(self):
        spec = GeometryTemplateSpec(template_id="jft051_sector")
        geometry = FakeGeometry()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflow = GeometryTemplateWorkflow(spec, root, run_id="20260722_120000")
            run = workflow.build(geometry)

            self.assertEqual(run.jmdl_path.name, "jft051_sector.jmdl")
            self.assertTrue(run.jmdl_path.is_file())
            manifest = json.loads(run.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "built")
            self.assertEqual(manifest["library_key"], "Custom Geometry\\Codex\\jft051_sector")
            self.assertEqual(
                geometry.events[0],
                ("build", 90.0, 100.0, {"angle": "Angle", "radius": "Radius"}),
            )
            with self.assertRaises(FileExistsError):
                GeometryTemplateWorkflow(spec, root, run_id="20260722_120000").build(FakeGeometry())

    def test_insert_sets_requested_values_and_verifies_them(self):
        spec = GeometryTemplateSpec(template_id="jft051_sector")
        geometry = FakeGeometry()
        with tempfile.TemporaryDirectory() as directory:
            workflow = GeometryTemplateWorkflow(spec, Path(directory), run_id="run")
            workflow.build(geometry)
            workflow.mark_registration_observed("Custom Geometry\\Codex\\jft051_sector")
            workflow.insert_and_verify(geometry)

        self.assertIn(
            ("insert", "Custom Geometry\\Codex\\jft051_sector", {}),
            geometry.events,
        )
        self.assertIn(
            ("set_equations", {"Angle": 30.0, "Radius": 100.0}),
            geometry.events,
        )

    def test_registration_cannot_be_marked_observed_before_build(self):
        workflow = GeometryTemplateWorkflow(
            GeometryTemplateSpec(template_id="jft051_sector"), Path("C:/runs"), run_id="run"
        )
        with self.assertRaises(RegistrationStateError):
            workflow.mark_registration_observed("Custom Geometry\\Codex\\jft051_sector")

    def test_registration_rejects_a_library_key_outside_the_template_namespace(self):
        geometry = FakeGeometry()
        with tempfile.TemporaryDirectory() as directory:
            workflow = GeometryTemplateWorkflow(
                GeometryTemplateSpec(template_id="jft051_sector"), Path(directory), run_id="run"
            )
            workflow.build(geometry)
            with self.assertRaises(ValueError):
                workflow.mark_registration_observed("Custom Geometry\\different")

    def test_ui_registration_stops_before_click_when_command_is_missing(self):
        ui = FakeUi(command=False)
        with self.assertRaises(UiControlNotFound):
            register_template_via_ui(ui, GeometryTemplateSpec(template_id="jft051_sector"))
        self.assertNotIn(("invoke", "Register in Geometry Library"), ui.events)


if __name__ == "__main__":
    unittest.main()
