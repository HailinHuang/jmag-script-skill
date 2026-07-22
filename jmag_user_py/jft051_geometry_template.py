"""Build, register, insert, and verify the JFT051 circular-sector template.

Run with the JMAG 25.1 Python runtime.  The ``register`` stage writes exactly
one item to the Geometry Library and therefore fails closed on any UI mismatch.
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Mapping

from jmag_functions.geometry_template_ui import register_template_via_ui
from jmag_functions.geometry_templates import GeometryTemplateSpec, GeometryTemplateWorkflow
from jmag_functions.project import create_application


JMAG_ROOT = Path(r"C:\Program Files\JMAG-Designer25.1")


def configure_jmag_runtime() -> None:
    """Make the JMAG package visible to the bundled Python interpreter."""
    root = str(JMAG_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


class JmagSectorAdapter:
    """JMAG Geometry Editor adapter used only by this live tutorial runner."""

    def __init__(self, geom_app: object) -> None:
        self.geom_app = geom_app
        self.document = None

    def build_sector(self, *, angle_deg: float, radius_mm: float, equation_names: Mapping[str, str]) -> None:
        self.document = self.geom_app.GetDocument()
        table = self.document.GetDesignTable()
        table.EditStart()
        try:
            for name, value in ((equation_names["angle"], angle_deg), (equation_names["radius"], radius_mm)):
                table.AddEquation(name)
                equation = table.GetEquation(name)
                equation.SetType(0)
                equation.SetExpression(str(value))
                equation.SetDescription("JFT051 geometry-template parameter")
                equation.SetRegistrationSource("")
                equation.SetRegisterToDesigner(0)
                equation.SetIsFactorKey(0)
                equation.SetTrueValue("")
                equation.SetFalseValue("")
                equation.SetDisplayName(name)
        finally:
            table.EditEnd()

        assembly = self.document.GetAssembly()
        sketch = assembly.CreateSketch(assembly.GetPlaneXY())
        sketch.SetName("JFT051_CircularSection")
        sketch.OpenSketch()
        try:
            angle_rad = math.radians(angle_deg)
            end_x = radius_mm * math.cos(angle_rad)
            end_y = radius_mm * math.sin(angle_rad)
            radial_x = sketch.CreateLine(0.0, 0.0, radius_mm, 0.0)
            arc = sketch.CreateArc(0.0, 0.0, radius_mm, 0.0, end_x, end_y)
            radial_end = sketch.CreateLine(end_x, end_y, 0.0, 0.0)
            if radial_x is None or arc is None or radial_end is None:
                raise RuntimeError("JMAG did not create the three sector edges")

            arc_ref = self.document.CreateReferenceFromItem(arc)
            radius_constraint = sketch.CreateMonoConstraint(11, arc_ref)
            if radius_constraint is None:
                raise RuntimeError("JMAG did not create the radius constraint")
            radius_constraint.SetEquation(equation_names["radius"])

            # The angle-from-X-axis constraint is attached to the second radial edge.
            angle_ref = self.document.CreateReferenceFromItem(radial_end)
            angle_constraint = sketch.CreateMonoConstraint("anglefromxaxis", angle_ref)
            if angle_constraint is None:
                raise RuntimeError("JMAG did not create the angle constraint")
            angle_constraint.SetEquation(equation_names["angle"])

            selection = self.document.GetSelection()
            selection.Clear()
            for item in (radial_x, arc, radial_end):
                selection.Add(item)
            sketch.CreateRegions()
            selection.Clear()
        finally:
            sketch.CloseSketch()
        self.document.UpdateModel(True, False)

    def save_as(self, path: Path) -> None:
        self.geom_app.SaveCurrentAs(str(path))

    def insert_library(self, library_key: str, rename_map: Mapping[str, str]) -> None:
        self.geom_app.InsertGeometryLibrary(library_key, dict(rename_map) if rename_map else None)
        self.document = self.geom_app.GetDocument()

    def set_equations(self, values: Mapping[str, float]) -> None:
        if self.document is None:
            raise RuntimeError("No Geometry Editor document is open")
        table = self.document.GetDesignTable()
        table.EditStart()
        try:
            for name, value in values.items():
                table.GetEquation(name).SetExpression(str(value))
        finally:
            table.EditEnd()
        self.document.UpdateModel(True, False)

    def read_equations(self, names: Mapping[str, str]) -> Mapping[str, float]:
        if self.document is None:
            raise RuntimeError("No Geometry Editor document is open")
        table = self.document.GetDesignTable()
        return {name: float(table.GetEquation(name).GetExpression()) for name in names.values()}


class PywinautoRegistrationUi:
    """UIA driver that refuses coordinate-only interaction with JMAG dialogs."""

    def __init__(self, screenshots: Path) -> None:
        try:
            from pywinauto import Desktop  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("register requires pywinauto; install it in the JMAG Python environment") from exc
        self.desktop = Desktop(backend="uia")
        self.screenshots = screenshots
        self.editor = None

    def ensure_editor_visible(self) -> None:
        editor = self.desktop.window(title_re=".*Geometry Editor.*")
        if not editor.exists(timeout=5):
            raise RuntimeError("Visible JMAG Geometry Editor window was not found")
        self.editor = editor
        editor.set_focus()

    def find_command(self, name: str) -> object | None:
        if self.editor is None:
            return None
        assembly = self.editor.child_window(title="Assembly", control_type="TreeItem")
        if not assembly.exists(timeout=2):
            return None
        assembly.right_click_input()
        menu = self.desktop.window(control_type="Menu")
        command = menu.child_window(title=name, control_type="MenuItem")
        return command if command.exists(timeout=2) else None

    def invoke(self, control: object) -> None:
        control.invoke()

    def wait_for_dialog(self, title: str) -> object | None:
        dialog = self.desktop.window(title_re=f".*{title}.*")
        return dialog if dialog.exists(timeout=5) else None

    def set_text(self, dialog: object, field: str, value: str) -> None:
        control = dialog.child_window(title=field, control_type="Edit")
        if not control.exists(timeout=2):
            raise RuntimeError(f"Registration field was not found: {field}")
        control.set_edit_text(value)

    def set_checked(self, dialog: object, field: str, value: bool) -> None:
        control = dialog.child_window(title_re=f".*{field}.*", control_type="CheckBox")
        if not control.exists(timeout=2):
            raise RuntimeError(f"Registration checkbox was not found: {field}")
        if bool(control.get_toggle_state()) != value:
            control.toggle()

    def confirm(self, dialog: object) -> None:
        button = dialog.child_window(title="OK", control_type="Button")
        if not button.exists(timeout=2):
            raise RuntimeError("Registration confirmation button was not found")
        button.invoke()

    def has_library_item(self, library_key: str) -> bool:
        if self.editor is None:
            return False
        item = self.editor.child_window(title=library_key.rsplit("\\", 1)[-1], control_type="TreeItem")
        return item.exists(timeout=5)

    def capture(self, label: str) -> None:
        if self.editor is not None:
            self.screenshots.mkdir(parents=True, exist_ok=True)
            self.editor.capture_as_image().save(self.screenshots / f"{label}.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("build", "register", "insert"))
    parser.add_argument("--run-root", type=Path, default=Path("tmp") / "geometry_templates")
    parser.add_argument("--template-id", default="jft051_sector")
    parser.add_argument("--run-id", default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--registered-library-key")
    args = parser.parse_args()

    spec = GeometryTemplateSpec(template_id=args.template_id)
    workflow = GeometryTemplateWorkflow(spec, args.run_root, run_id=args.run_id)
    configure_jmag_runtime()
    app = create_application(visible=True)
    geom = app.CreateGeometryEditor()
    adapter = JmagSectorAdapter(geom)
    try:
        if args.stage == "build":
            run = workflow.build(adapter)
            geom.Show()
            print(f"BUILT={run.jmdl_path}")
        elif args.stage == "register":
            run = workflow.build(adapter)
            geom.Show()
            register_template_via_ui(PywinautoRegistrationUi(run.run_dir / "screenshots"), spec)
            workflow.mark_registration_observed(spec.library_key)
            print(f"REGISTERED={spec.library_key}")
        else:
            if args.registered_library_key != spec.library_key:
                raise ValueError(
                    "insert requires --registered-library-key with the exact expected value "
                    f"'{spec.library_key}'"
                )
            # Insert only after a separately observed registration run.
            workflow.build(adapter)
            workflow.mark_registration_observed(args.registered_library_key)
            workflow.insert_and_verify(adapter)
            print(f"VERIFIED={spec.library_key}")
    finally:
        geom.Show()


if __name__ == "__main__":
    main()
