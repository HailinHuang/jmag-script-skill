"""Render a visual inventory table from an existing TestModel run report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from ._jmag_user_env import configure_environment
except ImportError:
    from _jmag_user_env import configure_environment

configure_environment()

from jmag_functions.inventory import export_inventory_html


def _normalize(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for record in records:
        if record.get("type") != "Equation" or "equation" in record:
            continue
        name = str(record.get("name", ""))
        equation_name = str(
            record.get("equation_name") or name.removeprefix("Equation parameters: ")
        )
        if equation_name:
            record["equation"] = {
                "name": equation_name,
                "display_name": record.get("display_name", ""),
                "description": record.get("description", ""),
                "expression": record.get("expression", record.get("value", "")),
                "evaluated_value": record.get("evaluated_value"),
            }
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    records = _normalize(report["before"]["parameters"])
    export_inventory_html(
        records,
        args.output,
        title=f"{report['model']} / {report['study']} / case {report['case']}",
    )
    print(args.output.resolve())


if __name__ == "__main__":
    main()
