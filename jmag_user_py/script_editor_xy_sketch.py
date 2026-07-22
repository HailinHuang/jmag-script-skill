"""JMAG Script Editor: save a copy, create an XY-plane circle sketch, and import it."""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_TARGET = Path(r"C:\Codex\jmag-script-skill\tmp\smoke.jproj")
SKETCH_NAME = "xy_circle_sketch"
RADIUS_PARAMETER = "radii1"
RADIUS = 45.0


def _add_radius_parameter(document: object, name: str, value: float) -> None:
    design_table = document.GetDesignTable()
    design_table.EditStart()
    try:
        design_table.AddEquation(name)
        equation = design_table.GetEquation(name)
        equation.SetType(0)
        equation.SetExpression(str(value))
        equation.SetDescription("")
        equation.SetRegistrationSource("")
        equation.SetRegisterToDesigner(0)
        equation.SetIsFactorKey(0)
        equation.SetTrueValue("")
        equation.SetFalseValue("")
        equation.SetDisplayName("")
    finally:
        design_table.EditEnd()


def run(app: object, target: Path) -> None:
    """Reproduce the recorded Geometry Editor workflow on a new project copy."""
    target = target.resolve()
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing project copy: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    app.SaveAs(str(target))
    app.LaunchGeometryEditor()
    geom_app = app.CreateGeometryEditor()
    document = geom_app.GetDocument()
    assembly = document.GetAssembly()

    xy_plane = assembly.GetPlaneXY()
    xy_reference = document.CreateReferenceFromItem(xy_plane)
    sketch = assembly.CreateSketch(xy_reference)
    sketch.SetName(SKETCH_NAME)
    sketch.OpenSketch()

    center = sketch.CreateVertex(0.0, 0.0)
    circle = sketch.CreateCircle(0.0, 0.0, RADIUS)

    center_reference = document.CreateReferenceFromItem(center)
    fixture = sketch.CreateMonoConstraint("fixture", center_reference)
    fixture.SetName("Fixture")

    _add_radius_parameter(document, RADIUS_PARAMETER, RADIUS)
    circle_reference = document.CreateReferenceFromItem(circle)
    radius_constraint = sketch.CreateMonoConstraint("radius", circle_reference)
    radius_constraint.SetProperty("Radius", RADIUS_PARAMETER)
    sketch.CloseSketch()

    app.ImportDataFromGeometryEditor()
    geom_app.SaveCurrent()
    app.Save()
    print(f"Saved JMAG project copy: {target}")
    print(f"Created XY sketch: {SKETCH_NAME}; radius parameter: {RADIUS_PARAMETER}={RADIUS}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()
    try:
        app = designer  # type: ignore[name-defined]
    except NameError as error:
        raise RuntimeError("Run this script from JMAG Designer Script Editor (Python 3.12).") from error
    run(app, args.target)


if __name__ == "__main__":
    main()
