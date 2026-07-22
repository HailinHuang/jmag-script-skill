"""Create a read-only visual Design Table inventory for TestModel1."""

from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path

try:
    from ._jmag_user_env import configure_environment
except ImportError:
    from _jmag_user_env import configure_environment

configure_environment()

from jmag.designer import designer

from jmag_functions import JMAGContext
from jmag_functions.inventory import export_inventory_html, inventory_design_table


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--study", default="kVA")
    parser.add_argument("--case", type=int, default=1)
    parser.add_argument("--status", type=Path)
    args = parser.parse_args()

    def status(stage: str, **details: object) -> None:
        if args.status is not None:
            args.status.parent.mkdir(parents=True, exist_ok=True)
            args.status.write_text(
                json.dumps({"stage": stage, **details}, indent=2),
                encoding="utf-8",
            )

    status("creating_application")
    app = designer.CreateApplication(["-g"])
    try:
        status("loading_project")
        app.Load(str(args.project.resolve()))
        status("inventory")
        context = JMAGContext.from_current(app, study=args.study)
        records = inventory_design_table(context, case=args.case)
        status("rendering", parameters=len(records))
        output = export_inventory_html(
            records,
            args.output,
            title=f"{context.model.GetName()} / {context.study.GetName()} / case {args.case}",
        )
        equation_count = sum(record["type"] == "Equation" for record in records)
        related_count = sum(
            bool(record["relationships"]["references"])
            for record in records
        )
        print(
            f"output={output}; parameters={len(records)}; equations={equation_count}; "
            f"expression_relationships={related_count}"
        )
        status("complete", output=str(output), parameters=len(records))
    except Exception as exc:
        status("error", error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc())
        raise
    finally:
        status("closing")
        app.Quit()


if __name__ == "__main__":
    main()
