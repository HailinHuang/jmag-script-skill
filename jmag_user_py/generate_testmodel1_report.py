"""Generate the TestModel1 parameter and function-candidate report."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

try:
    from ._jmag_user_env import configure_environment
except ImportError:
    from _jmag_user_env import configure_environment

configure_environment()


PURPOSES = {
    "PMangle2": "Second magnet segment angle; controls rotor PM geometry.",
    "Rri": "Rotor inner radius CAD variable.",
    "Ri": "Rotor inner radius used by the parametric geometry.",
    "Rso": "Stator outer radius.",
    "airgap": "Mechanical air-gap length.",
    "arcangle1": "First rotor/magnet arc angle.",
    "arcangle2": "Second rotor/magnet arc angle.",
    "d1": "Local rotor/magnet geometry offset d1.",
    "d2": "Local rotor/magnet geometry offset d2.",
    "d3": "Local rotor/magnet geometry offset d3.",
    "d4": "Local rotor/magnet geometry offset d4.",
    "dPM1": "First permanent-magnet thickness parameter.",
    "dPM2": "Second permanent-magnet thickness parameter.",
    "dair": "Local air-region clearance in the rotor geometry.",
    "dbridge11": "Rotor bridge thickness for bridge 1-1.",
    "dbridge12": "Rotor bridge thickness for bridge 1-2.",
    "dbridge21": "Rotor bridge thickness for bridge 2-1.",
    "dbridge22": "Rotor bridge thickness for bridge 2-2.",
    "dbridge23": "Rotor bridge thickness for bridge 2-3.",
    "dslot": "Rotor/stator slot local width or clearance parameter.",
    "dso": "Slot-opening width parameter.",
    "dyoke": "Stator yoke radial thickness.",
    "hcore1": "First rotor core height parameter.",
    "hcore2": "Second rotor core height parameter.",
    "hslot": "Stator slot height.",
    "hso": "Stator slot-opening height.",
    "hwedge": "Slot-wedge height.",
    "lPM1": "First permanent-magnet length parameter.",
    "lPM21": "Second PM section length, segment 1.",
    "lPM22": "Second PM section length, segment 2.",
    "lPMslot21": "Second PM-slot length, segment 1.",
    "lPMslot22": "Second PM-slot length, segment 2.",
    "lbridge11": "Rotor bridge length for bridge 1-1.",
    "lbridge12": "Rotor bridge length for bridge 1-2.",
    "lbridge21": "Rotor bridge length for bridge 2-1.",
    "lbridge22": "Rotor bridge length for bridge 2-2.",
    "lbridge23": "Rotor bridge length for bridge 2-3.",
    "r0": "Local geometry fillet radius r0.",
    "r1": "Local geometry fillet radius r1.",
    "ModelThickness": "2-D model extrusion/stack thickness used by the study.",
    "Step": "Total transient sample points; derived as intervals plus the initial point.",
    "StepDivision": "Study step-division setting linked to the Div equation.",
    "PhaseU": "Phase-U angle applied to the three-phase current source.",
    "InitialRotationAngle": "Initial mechanical rotor angle applied to the motion condition.",
    "Vline_limit": "Maximum allowed line voltage for operating-point checks.",
    "Initial_Position": "Initial rotor position derived from slot/pole geometry.",
    "J_limit": "Current-density limit used to derive the allowable RMS current.",
    "ab": "Number of parallel winding branches.",
    "fre": "Electrical frequency derived from speed and pole count.",
    "Poles": "Pole count used by the electrical-frequency expression.",
    "Phase_Advance": "Current phase-advance angle.",
    "Copper_Resistivity": "Copper resistivity assigned to the electromagnetic model.",
    "Conductor_Layer": "Number of conductor layers used by the slot-fill expression.",
    "speed": "Mechanical rotor speed in r/min.",
    "Magnet_Conductivity": "Electrical conductivity assigned to the permanent magnets.",
    "CoilEnd": "End-winding modeling/control flag.",
    "Torque_Required": "Target torque used by the operating-point/optimization setup.",
    "Stack_Length": "Active axial stack length used in loss and mass calculations.",
    "poles": "Pole count used by geometric end-winding expressions.",
    "Conductor_Layers": "Conductor-layer count used in copper-loss calculations.",
    "Slot_Number": "Stator slot count.",
    "Tem_Magnets": "Magnet operating temperature.",
    "Tem_End_Winding": "End-winding conductor temperature.",
    "DC_Copper_Lossef": "Calculated active-length DC copper loss.",
    "End_Winding_Length": "Estimated end-winding conductor length.",
    "DC_Copper_Lossend": "Calculated end-winding DC copper loss.",
    "End_Winding_Height": "Estimated axial/radial end-winding envelope height.",
    "Cu_Tem_Cof": "Copper temperature coefficient of resistivity.",
    "Magnet_Tem_Cof": "Magnet temperature coefficient used by project calculations.",
    "Rsi": "Derived stator inner radius.",
    "Area_Slot": "Derived usable slot area.",
    "Slot_Fill_Factor": "Conductor area divided by usable slot area.",
    "Irms_limit": "Allowable RMS current derived from current density, conductor area and branches.",
    "ProcessNo": "Project workflow/optimization process selector.",
    "margin_ratio": "Engineering margin multiplier used by project constraints.",
    "Phase0": "Baseline/reference current phase angle.",
    "Irms": "Applied RMS phase current.",
    "kVA_Ratio": "Project apparent-power scaling or constraint ratio.",
    "kVA_Cost": "Project cost/objective contribution associated with kVA.",
    "objT": "Project optimization objective value/target variable.",
    "IRange0": "Lower/current-range control value for the project workflow.",
    "IRange1": "Upper/secondary current-range control value for the project workflow.",
    "mesh_ratio": "Global mesh-density scaling factor.",
    "Div_Period": "Number of modeled periods used in transient step derivation.",
    "Div": "Base transient divisions; changed from 60 to 8 for this test.",
    "Curesistivity_Eff": "Temperature-adjusted copper resistivity for active conductors.",
    "Curesistivity_End": "Temperature-adjusted copper resistivity for end windings.",
    "Tem_Eff_Winding": "Active-winding conductor temperature.",
}


def _short_name(record: dict[str, Any]) -> str:
    name = record["name"]
    if name.startswith("CAD parameters: "):
        return name.removeprefix("CAD parameters: ").removesuffix("@Variables")
    if name.startswith("Equation parameters: "):
        return name.removeprefix("Equation parameters: ")
    if name.startswith("Study Properties: "):
        return name.removeprefix("Study Properties: ")
    if "PhaseU" in name:
        return "PhaseU"
    if "InitialRotationAngle" in name:
        return "InitialRotationAngle"
    return name


def _purpose(record: dict[str, Any]) -> str:
    short = _short_name(record)
    if short in PURPOSES:
        purpose = PURPOSES[short]
    elif short.startswith("Area_"):
        purpose = f"Measured cross-sectional area for {short.removeprefix('Area_')}."
    else:
        purpose = "Project-specific parameter; its precise semantic role is not documented in the model."
    if record["type"] == "Real" and record["name"].startswith("CAD parameters: "):
        purpose = "CAD input synchronized to the corresponding geometry variable. " + purpose
    return purpose


def _escape(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return str(value).replace("|", "\\|").replace("\n", " ")


def _parse_case_values(rows: list[list[str]]) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for name, value in zip(rows[0], rows[1]):
        values.setdefault(name, []).append(value)
    return values


def _read_case_values(path: Path) -> dict[str, list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    return _parse_case_values(rows)


def _display_result(values: list[str] | None) -> str:
    if not values:
        return "not exported"
    if len(values) == 1:
        return values[0]
    return "; ".join(values) + " (duplicate JMAG columns)"


def generate(run_report: Path) -> str:
    report = json.loads(run_report.read_text(encoding="utf-8"))
    output_dir = run_report.parent
    results = _read_case_values(output_dir / "case_values.csv")
    after_by_index = {item["index"]: item for item in report["after"]["parameters"]}
    selected = [
        "Average_Torque", "Vline", "Irms", "CuLoss_eff", "PM_Loss",
        "IronLoss_Syoke", "IronLoss_Steeth", "IronLoss_Rotor", "Losstotal",
        "Slot_Fill_Factor",
    ]

    lines = [
        "# TestModel1 JMAG Function Test Report",
        "",
        "## Outcome",
        "",
        f"- Source project: `{report['source_project']}` (loaded only; not saved).",
        f"- Test copy: `{report['project_copy']}`.",
        f"- Model / study / case: `{report['model']}` / `{report['study']}` / `{report['case']}`.",
        f"- Step relation: `{report['step_formula']}`.",
        f"- Before: `Div={report['before']['div']}`, {report['before']['intervals']} intervals, {report['before']['points']} points.",
        f"- After: `Div={report['after']['div']}`, {report['after']['intervals']} intervals, {report['after']['points']} points.",
        f"- JMAG load, mutation, solve and export time reported by the script: {report['elapsed_seconds']} s.",
        "",
        "`Step` was not overwritten with a literal. The existing dependency was preserved: "
        "`Div=60 -> 8`, while `Div_Period=1` and the Step expression remain unchanged.",
        "",
        "## Selected solver results",
        "",
        "The user did not name individual response quantities, so the script exported the complete "
        "case-value table and the complete Step result tables. The following common motor metrics "
        "are highlighted from that complete export:",
        "",
        "| Result | Value |",
        "| --- | ---: |",
    ]
    for name in selected:
        lines.append(f"| `{name}` | {_escape(_display_result(results.get(name)))} |")

    lines.extend(
        [
            "",
            "## Parameter inventory and purpose analysis",
            "",
            "Purposes are engineering interpretations based on parameter names and expressions. "
            "Blank JMAG descriptions mean these interpretations are not authoritative model documentation.",
            "",
            "| # | Type | Parameter | Before | After | Expression | Recorded purpose |",
            "| ---: | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for before in report["before"]["parameters"]:
        after = after_by_index[before["index"]]
        expression = before.get("expression", "")
        lines.append(
            "| {index} | {type} | `{name}` | {before_value} | {after_value} | "
            "{expression} | {purpose} |".format(
                index=before["index"],
                type=_escape(before["type"]),
                name=_escape(before["name"]),
                before_value=_escape(before.get("value", "")),
                after_value=_escape(after.get("value", "")),
                expression=f"`{_escape(expression)}`" if expression else "",
                purpose=_escape(_purpose(before)),
            )
        )

    lines.extend(
        [
            "",
            "## What should become reusable functions",
            "",
            "| Operation | Recommendation | Reason / boundary |",
            "| --- | --- | --- |",
            "| Load a project and save a protected copy | Candidate: `load_project_copy` | Reusable safety boundary; source/target paths must remain caller configuration. |",
            "| Enumerate every Design Table parameter and Equation metadata | Candidate: `inventory_design_table` | Real TestModel1 evidence exists, including graceful handling of an Equation wrapper that cannot be materialized. |",
            "| Set one or several equation parameters | Reuse `set_parameter` / `set_parameters` | Existing library API succeeded against real JMAG 25.1 with `Div`. |",
            "| Apply CAD parameters and run selected cases | Extend/review `run_cases` or add explicit orchestration | `ApplyAllCasesCadParameters` is Help-verified and was required before this run; result deletion must remain explicit. |",
            "| Read named response values | Reuse/extend `get_value` / `get_values` | Result names and cases remain caller configuration. |",
            "| Export Design Table | Candidate: `export_design_table` | Thin Help-verified wrapper with output-path validation. |",
            "| Export response value table | Candidate: `export_case_values` | General operation, distinct from selecting named responses. |",
            "| Export full result tables | Candidate with explicit axis policy | `Step`, `Time`, `Angle`, or `Distance` must be selected by the caller. |",
            "| Convert 90 intervals to `Div=8` | Do not generalize as a JMAG function | It depends on TestModel1's project equation `Step = Div / Div_Period * 1.5 + 1`. |",
            "| Parameter-purpose text in this report | Do not encode as API behavior | It is engineering interpretation and belongs in model documentation/configuration. |",
            "",
            "No candidate should be promoted automatically. `inventory_design_table` has real-project "
            "evidence from TestModel1, while project loading, export policies and run orchestration still "
            "need isolated tests before catalog publication.",
            "",
            "## JMAG 25.1 Help evidence",
            "",
            "- `Designer/classApplication.html`: `Load` anchor `af72d1bec02cac3c005fe554aa258b8d9`; `SaveAs` anchor `aec8db8d7e6949bc5a777e5f8e2e505aa`.",
            "- `Designer/classDesignTable.html`: `NumParameters`, `ParameterName`, `ParameterTypeName`, `GetValue`, `SetValue`, and `Export`.",
            "- `Designer/classParametricEquation.html`: `GetName`, `GetDisplayName`, `GetDescription`, `GetExpression`, and zero-based `GetValue`.",
            "- `Designer/classStudy.html`: `ApplyAllCasesCadParameters`, `Run`, `GetResponseData`, `ExportCaseValueData`, and `GetResultTable`.",
            "- `Designer/classResultTable.html`: `WriteAllCaseTables(filename, type)`.",
            "",
            "## Produced evidence",
            "",
            "- `design_table_before.csv` and `design_table_after.csv`: complete case parameter tables.",
            "- `case_values.csv`: complete response value table.",
            "- `result_tables.csv`: complete Step-axis result tables (260 CSV lines).",
            "- `run_report.json`: machine-readable before/after inventory and run metadata.",
            "- `TestModel1_steps12.jproj` plus `.jfiles`: saved runnable test copy and result files.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(generate(args.run_report), encoding="utf-8")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
