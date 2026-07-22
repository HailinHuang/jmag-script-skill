"""Create and persist a minimal Geometry Editor sketch in a protected project copy."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

try:
    from ._jmag_user_env import configure_environment
except ImportError:
    from _jmag_user_env import configure_environment

configure_environment()

from jmag_functions.project import create_application, load_project_copy


DEFAULT_PROJECT = Path(r"C:\JMAG_Models\TestModel1.jproj")
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "tmp"


def _item_names(assembly: object) -> list[str]:
    names: list[str] = []
    for index in range(assembly.NumItems()):
        item = assembly.GetItem(index)
        names.append(item.GetName())
    return names


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    source = args.project.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = output_dir / f"TestModel1_geometry_smoke_{stamp}.jproj"
    sketch_name = f"codex_geometry_smoke_{stamp}"

    session = load_project_copy(source, target)
    app = session.app
    geom = None
    try:
        model = app.GetCurrentModel()
        if not model.IsCadLinkOpen():
            model.RestoreCadLink(False)
        if not model.IsCadLinkOpen():
            raise RuntimeError("CAD link remains closed after RestoreCadLink")

        geom = app.CreateGeometryEditor(False)
        document = geom.GetDocument()
        assembly = document.GetAssembly()
        item_count_before = assembly.NumItems()

        sketch = assembly.CreateSketch()
        sketch.SetName(sketch_name)
        sketch.CreateCircle(0.0, 0.0, 1.0)
        sketch.CloseSketch()

        item_count_after = assembly.NumItems()
        if item_count_after != item_count_before + 1:
            raise RuntimeError(
                f"Sketch count did not increase: {item_count_before} -> {item_count_after}"
            )
        if sketch_name not in _item_names(assembly):
            raise RuntimeError(f"New sketch is absent before save: {sketch_name}")

        document.UpdateModel(True, False)
        print(f"COPY={target}")
        print(f"SKETCH={sketch_name}")
        print(f"ITEM_COUNT={item_count_before}->{item_count_after}")
        print("WRITEBACK_COMPLETED")
    finally:
        if geom is not None:
            geom.Quit()
        session.close()

    verify_app = create_application(visible=False)
    verify_geom = None
    try:
        verify_app.Load(str(target))
        verify_geom = verify_app.CreateGeometryEditor(False)
        verify_assembly = verify_geom.GetDocument().GetAssembly()
        if sketch_name not in _item_names(verify_assembly):
            raise RuntimeError(f"Persisted sketch is absent after reopen: {sketch_name}")
        print("REOPEN_VERIFIED")
    finally:
        if verify_geom is not None:
            verify_geom.Quit()
        verify_app.Quit()


if __name__ == "__main__":
    main()
