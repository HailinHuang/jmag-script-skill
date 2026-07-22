# -*- coding: utf-8 -*-
"""
JMAG Geometry Template Tool
===========================

Purpose
-------
1. Open JMAG Geometry Editor.
2. Build a parametric 2-D annulus from two concentric circles.
3. Convert the closed loops into one region with an inner hole.
4. Save the geometry as a .jmdl file.
5. Optionally insert a geometry that has already been registered in the
   JMAG Geometry Library.

Execution modes
---------------
A. Run inside JMAG Script Editor:
       Open this file and run it. The built-in global ``designer`` is used.

B. Run from an external Windows Python interpreter:
       Install pywin32, then execute:
           py -m pip install pywin32
           py jmag_geometry_template_tool.py

Notes
-----
- The script intentionally keeps configuration at the top of the file so it
  can also be used in older JMAG embedded Python environments.
- Geometry-library registration is treated as a one-time GUI operation.
  After registration, capture the library key from a recorded insertion script
  and set REGISTERED_LIBRARY_KEY below.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional


# =============================================================================
# User configuration
# =============================================================================

# "build": create and save an annulus .jmdl
# "insert": insert an already registered Geometry Library item
MODE = "build"

REPO_ROOT = r"C:\Codex\jmag-script-skill"
OUTPUT_JMDL = os.path.join(
    REPO_ROOT,
    "artifacts",
    "geometry_library",
    "annulus_2d.jmdl",
)

CREATE_NEW_DOCUMENT = True
OVERWRITE_OUTPUT = True

# Set this only after the geometry has been registered once in the GUI.
# Recommended method:
# 1. Start JMAG script recording.
# 2. Insert the registered geometry manually.
# 3. Copy the string passed to InsertGeometryLibrary(...).
REGISTERED_LIBRARY_KEY = u""

# Geometry dimensions use the active Geometry Editor length unit.
ANNULUS_NAME = u"Annulus2D"
CENTER_X = 0.0
CENTER_Y = 0.0
INNER_RADIUS = 20.0
OUTER_RADIUS = 40.0


@dataclass(frozen=True)
class AnnulusSpec:
    """Parameters and stable object names for one annular 2-D template."""

    name: str = ANNULUS_NAME
    center_x: float = CENTER_X
    center_y: float = CENTER_Y
    inner_radius: float = INNER_RADIUS
    outer_radius: float = OUTER_RADIUS

    @property
    def sketch_name(self) -> str:
        return f"{self.name}_Sketch"

    @property
    def outer_circle_name(self) -> str:
        return f"{self.name}_OuterCircle"

    @property
    def inner_circle_name(self) -> str:
        return f"{self.name}_InnerCircle"

    @property
    def region_name(self) -> str:
        return f"{self.name}_Region"

    @property
    def equation_prefix(self) -> str:
        return self.name.lower()


# =============================================================================
# JMAG application acquisition
# =============================================================================

def get_jmag_application() -> Any:
    """
    Return the JMAG Designer application.

    Inside JMAG Script Editor, the global ``designer`` object is used.
    From external Python, COM automation is used through pywin32.
    """
    try:
        # ``designer`` is injected by JMAG Script Editor.
        return designer.GetApplication()  # type: ignore[name-defined]
    except NameError:
        pass

    try:
        import win32com.client  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "External execution requires pywin32. Install it with:\n"
            "  py -m pip install pywin32\n"
            "Alternatively, run this file in JMAG Script Editor."
        ) from exc

    try:
        app = win32com.client.Dispatch("designer.Application")
        app.Show()
        return app
    except Exception as exc:
        raise RuntimeError(
            "Could not start or connect to JMAG Designer through COM. "
            "Confirm that JMAG is installed and its automation server is registered."
        ) from exc


# =============================================================================
# Validation and utility functions
# =============================================================================

def validate_spec(spec: AnnulusSpec) -> None:
    """Reject invalid annulus dimensions before any JMAG API call."""
    if not spec.name.strip():
        raise ValueError("The geometry name must not be empty.")
    if spec.inner_radius <= 0.0:
        raise ValueError("INNER_RADIUS must be greater than zero.")
    if spec.outer_radius <= spec.inner_radius:
        raise ValueError("OUTER_RADIUS must be greater than INNER_RADIUS.")


def ensure_parent_directory(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def remove_existing_output(path: str) -> None:
    if not os.path.exists(path):
        return
    if not OVERWRITE_OUTPUT:
        raise FileExistsError(
            f"Output already exists: {path}\n"
            "Set OVERWRITE_OUTPUT = True or change OUTPUT_JMDL."
        )
    os.remove(path)


def signed_axis_expression(value: float, equation_name: str) -> str:
    """
    JMAG distance-from-axis constraints are unsigned.

    A negative center coordinate is represented by the negative of the
    corresponding positive-valued equation.
    """
    if value < 0.0:
        return f"-{equation_name}"
    return equation_name


def add_scalar_equation(design_table: Any, name: str, value: float) -> None:
    """Add one scalar equation to the Geometry Editor design table."""
    design_table.AddEquation(name)
    equation = design_table.GetEquation(name)
    equation.SetType(0)
    equation.SetExpression(str(abs(value)))
    equation.SetDescription("")
    equation.SetRegistrationSource("")
    equation.SetRegisterToDesigner(0)
    equation.SetIsFactorKey(0)
    equation.SetTrueValue("")
    equation.SetFalseValue("")
    equation.SetDisplayName(name)


def create_annulus_equations(geom_document: Any, spec: AnnulusSpec) -> dict[str, str]:
    """Create the four equations used by the annulus constraints."""
    names = {
        "center_x": f"{spec.equation_prefix}_center_x",
        "center_y": f"{spec.equation_prefix}_center_y",
        "inner_radius": f"{spec.equation_prefix}_inner_radius",
        "outer_radius": f"{spec.equation_prefix}_outer_radius",
    }

    design_table = geom_document.GetDesignTable()
    design_table.EditStart()
    try:
        add_scalar_equation(design_table, names["center_x"], spec.center_x)
        add_scalar_equation(design_table, names["center_y"], spec.center_y)
        add_scalar_equation(design_table, names["inner_radius"], spec.inner_radius)
        add_scalar_equation(design_table, names["outer_radius"], spec.outer_radius)
    finally:
        design_table.EditEnd()

    return names


def find_last_region_item(sketch: Any) -> Optional[Any]:
    """Return the last RegionItem currently held by a sketch."""
    last_region = None
    for index in range(sketch.NumItems()):
        item = sketch.GetItem(index)
        try:
            script_type = item.GetScriptTypeName()
        except Exception:
            continue
        if script_type == u"RegionItem":
            last_region = item
    return last_region


# =============================================================================
# Geometry construction
# =============================================================================

def create_annulus_2d(geom_document: Any, spec: AnnulusSpec) -> Any:
    """
    Create a constrained annulus in an assembly-level XY sketch.

    Two selected closed circles are passed to CreateRegions(). JMAG interprets
    the inner closed loop as a hole in the outer region.
    """
    validate_spec(spec)
    equations = create_annulus_equations(geom_document, spec)

    assembly = geom_document.GetAssembly()
    sketch = assembly.CreateSketch(assembly.GetPlaneXY())
    sketch.SetName(spec.sketch_name)
    sketch.OpenSketch()

    try:
        outer_circle = sketch.CreateCircle(
            spec.center_x,
            spec.center_y,
            spec.outer_radius,
        )
        outer_circle.SetName(spec.outer_circle_name)

        inner_circle = sketch.CreateCircle(
            spec.center_x,
            spec.center_y,
            spec.inner_radius,
        )
        inner_circle.SetName(spec.inner_circle_name)

        outer_ref = sketch.CreateReferenceFromItem(outer_circle)
        inner_ref = sketch.CreateReferenceFromItem(inner_circle)

        # Keep both circles concentric.
        sketch.CreateBiConstraint(
            u"concentricity",
            outer_ref,
            inner_ref,
        )

        # Parameterise the shared centre with signed distance-from-axis
        # constraints on the outer circle's centre vertex.
        center_vertex = outer_circle.GetCenterVertex()
        center_ref = sketch.CreateReferenceFromItem(center_vertex)

        center_x_constraint = sketch.CreateMonoConstraint(
            u"distancefromyaxis",
            center_ref,
        )
        center_x_constraint.SetEquation(
            signed_axis_expression(spec.center_x, equations["center_x"])
        )

        center_y_constraint = sketch.CreateMonoConstraint(
            u"distancefromxaxis",
            center_ref,
        )
        center_y_constraint.SetEquation(
            signed_axis_expression(spec.center_y, equations["center_y"])
        )

        outer_radius_constraint = sketch.CreateMonoConstraint(
            u"radius",
            outer_ref,
        )
        outer_radius_constraint.SetEquation(equations["outer_radius"])

        inner_radius_constraint = sketch.CreateMonoConstraint(
            u"radius",
            inner_ref,
        )
        inner_radius_constraint.SetEquation(equations["inner_radius"])

        # Convert both closed loops into a single annular region.
        sketch.SelectItem(outer_circle)
        sketch.SelectItem(inner_circle)
        sketch.CreateRegions()

        region = find_last_region_item(sketch)
        if region is None:
            raise RuntimeError(
                "JMAG did not create a RegionItem from the two circles."
            )
        region.SetName(spec.region_name)
        return region
    finally:
        sketch.CloseSketch()


# =============================================================================
# Tool modes
# =============================================================================

def build_geometry_template(app: Any, spec: AnnulusSpec) -> None:
    """Open Geometry Editor, build the annulus, and save the .jmdl file."""
    geom_app = app.CreateGeometryEditor()

    if CREATE_NEW_DOCUMENT:
        geom_app.NewDocument()

    geom_document = geom_app.GetDocument()
    create_annulus_2d(geom_document, spec)

    ensure_parent_directory(OUTPUT_JMDL)
    remove_existing_output(OUTPUT_JMDL)
    geom_app.SaveCurrentAs(OUTPUT_JMDL)

    # Keep the editor visible for inspection and the one-time library
    # registration workflow.
    geom_app.Show()
    geom_app.Raise()
    geom_app.View()

    print("=" * 72)
    print("JMAG annulus geometry created.")
    print(f"Saved JMDL: {OUTPUT_JMDL}")
    print("")
    print("Next step for Geometry Library use:")
    print("1. Register this model once under Custom Geometry > 2D Basics.")
    print("2. Record a manual insertion and copy its library key.")
    print("3. Set MODE = 'insert' and REGISTERED_LIBRARY_KEY in this file.")
    print("=" * 72)


def insert_registered_geometry(app: Any) -> None:
    """Insert an already registered Geometry Library item."""
    library_key = REGISTERED_LIBRARY_KEY.strip()
    if not library_key:
        raise ValueError(
            "REGISTERED_LIBRARY_KEY is empty.\n"
            "Register the generated geometry once, record a manual insertion, "
            "and copy the key used by InsertGeometryLibrary(...)."
        )

    geom_app = app.CreateGeometryEditor()
    geom_app.InsertGeometryLibrary(library_key)
    geom_app.Show()
    geom_app.Raise()
    geom_app.View()

    print(f"Inserted Geometry Library item: {library_key}")


def main() -> None:
    app = get_jmag_application()
    spec = AnnulusSpec()

    selected_mode = MODE.strip().lower()
    if selected_mode == "build":
        build_geometry_template(app, spec)
    elif selected_mode == "insert":
        insert_registered_geometry(app)
    else:
        raise ValueError("MODE must be either 'build' or 'insert'.")


if __name__ == "__main__":
    main()
