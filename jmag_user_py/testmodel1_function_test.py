"""Run the TestModel1 step-reduction function test in JMAG Designer 25.1.

The source project is never saved. A project copy and all exported evidence are
written to a newly created output directory.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

try:
    from ._jmag_user_env import configure_environment
except ImportError:
    from _jmag_user_env import configure_environment

configure_environment()

from jmag_functions import JMAGContext, get_value, run_cases, set_parameter
from jmag_functions.exports import (
    export_case_values,
    export_design_table,
    export_result_tables,
)
from jmag_functions.inventory import inventory_design_table
from jmag_functions.project import load_project_copy


STEP_RATIO = 1.5


@dataclass(frozen=True)
class TestConfig:
    source_project: Path
    output_dir: Path
    study_name: str = "kVA"
    case: int = 1
    original_intervals: int = 90
    target_intervals: int = 12


def calculate_div_for_intervals(
    target_intervals: int,
    *,
    div_period: float,
    step_ratio: float = STEP_RATIO,
) -> int:
    """Return Div while preserving Step = Div / Div_Period * ratio + 1."""
    if isinstance(target_intervals, bool) or target_intervals < 1:
        raise ValueError("target_intervals must be a positive integer")
    if div_period <= 0 or step_ratio <= 0:
        raise ValueError("div_period and step_ratio must be positive")
    div = target_intervals * div_period / step_ratio
    rounded = round(div)
    if not math.isclose(div, rounded, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError(
            "target intervals cannot preserve the existing Step equation "
            "with an integer Div"
        )
    return int(rounded)


def _parameter_value(records: list[dict[str, object]], name: str) -> object:
    for record in records:
        if record["name"] == name:
            return record["value"]
    raise KeyError(f"JMAG design-table parameter not found: {name}")


def run_function_test(config: TestConfig) -> dict[str, object]:
    """Execute the authorized TestModel1 test against a newly saved copy."""
    source = config.source_project.resolve()
    output_dir = config.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    project_copy = output_dir / f"{source.stem}_steps{config.target_intervals}.jproj"
    started = time.time()

    with load_project_copy(source, project_copy) as project:
        context = JMAGContext.from_current(project.app, study=config.study_name)
        before_parameters = inventory_design_table(context, config.case)
        export_design_table(context, output_dir / "design_table_before.csv")

        current_div = float(get_value(context, "Div", config.case))
        div_period = float(get_value(context, "Div_Period", config.case))
        current_intervals = current_div / div_period * STEP_RATIO
        if not math.isclose(current_intervals, config.original_intervals):
            raise ValueError(
                f"expected {config.original_intervals} intervals; got {current_intervals}"
            )

        target_div = calculate_div_for_intervals(
            config.target_intervals, div_period=div_period
        )
        set_parameter(context, "Div", target_div, config.case)
        context.study.ApplyAllCasesCadParameters()
        updated_parameters = inventory_design_table(context, config.case)
        derived_points = int(
            _parameter_value(updated_parameters, "Study Properties: Step")
        )
        expected_points = config.target_intervals + 1
        if derived_points != expected_points:
            raise RuntimeError(
                f"Step derivation did not update: expected {expected_points}, "
                f"got {derived_points}"
            )

        run_cases(
            context,
            config.case,
            clear_results=True,
            apply_cad_parameters=True,
        )
        export_design_table(context, output_dir / "design_table_after.csv")
        export_case_values(context, output_dir / "case_values.csv")
        export_result_tables(
            context, output_dir / "result_tables.csv", axis="Step"
        )
        after_parameters = inventory_design_table(context, config.case)
        project.save()

        report: dict[str, object] = {
            "source_project": str(source),
            "project_copy": str(project_copy),
            "model": str(context.model.GetName()),
            "study": str(context.study.GetName()),
            "case": config.case,
            "step_formula": "Step = Div / Div_Period * 1.5 + 1",
            "before": {
                "div": current_div,
                "div_period": div_period,
                "intervals": current_intervals,
                "points": int(current_intervals + 1),
                "parameters": before_parameters,
            },
            "after": {
                "div": target_div,
                "div_period": div_period,
                "intervals": config.target_intervals,
                "points": derived_points,
                "parameters": after_parameters,
            },
            "exports": {
                "design_table_before": str(output_dir / "design_table_before.csv"),
                "design_table_after": str(output_dir / "design_table_after.csv"),
                "case_values": str(output_dir / "case_values.csv"),
                "result_tables": str(output_dir / "result_tables.csv"),
            },
            "elapsed_seconds": round(time.time() - started, 3),
        }
        (output_dir / "run_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--study", default="kVA")
    parser.add_argument("--case", type=int, default=1)
    parser.add_argument("--target-intervals", type=int, default=12)
    args = parser.parse_args()
    report = run_function_test(
        TestConfig(
            source_project=args.source,
            output_dir=args.output,
            study_name=args.study,
            case=args.case,
            target_intervals=args.target_intervals,
        )
    )
    print(
        json.dumps(
            {
                key: report[key]
                for key in ("project_copy", "exports", "elapsed_seconds")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
