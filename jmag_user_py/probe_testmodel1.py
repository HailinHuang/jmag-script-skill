"""Read-only inventory probe for a JMAG project.

Run this with the Python bundled in JMAG Designer. The probe loads a project,
records studies and design-table equations, and quits without saving.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

try:
    from ._jmag_user_env import configure_environment
except ImportError:
    from _jmag_user_env import configure_environment

configure_environment()

from jmag.designer import designer


def _safe(call: Callable[[], Any]) -> Any:
    try:
        value = call()
    except Exception as exc:  # JMAG wrapper exceptions vary by object type.
        return {"error": f"{type(exc).__name__}: {exc}"}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return list(value)
    except TypeError:
        return str(value)


def _equation_record(table: Any, parameter_index: int) -> dict[str, Any]:
    parameter_name = str(table.ParameterName(parameter_index))
    equation_name = parameter_name.removeprefix("Equation parameters: ")
    base = {
        "parameter_index": parameter_index,
        "parameter_name": parameter_name,
        "name": equation_name,
    }
    if not equation_name:
        return {**base, "error": "Equation parameter has no name"}
    try:
        equation = table.GetEquation(equation_name)
    except Exception as exc:
        return {**base, "error": f"{type(exc).__name__}: {exc}"}
    values = [
        _safe(lambda case_index=case_index: equation.GetValue(case_index))
        for case_index in range(int(table.NumCases()))
    ]
    return {
        **base,
        "display_name": _safe(equation.GetDisplayName),
        "description": _safe(equation.GetDescription),
        "expression": _safe(equation.GetExpression),
        "type": _safe(equation.GetType),
        "modeling": _safe(equation.GetModeling),
        "valid": _safe(equation.IsValid),
        "values_by_one_based_case": {
            str(index + 1): value for index, value in enumerate(values)
        },
        "related_parameter_names": _safe(
            lambda: table.GetRelatedParameterNames(equation_name)
        ),
    }


def probe(project: Path) -> dict[str, Any]:
    app = designer.CreateApplication(["-g"])
    try:
        app.Load(str(project))
        model = app.GetCurrentModel()
        if model is None:
            raise RuntimeError("JMAG loaded the project without a current model")

        studies = []
        for study_index in range(int(model.NumStudies())):
            study = model.GetStudy(study_index)
            table = study.GetDesignTable()
            parameters = []
            equations = []
            for parameter_index in range(int(table.NumParameters())):
                parameter_type = str(table.ParameterTypeName(parameter_index))
                parameter = {
                    "index": parameter_index,
                    "name": str(table.ParameterName(parameter_index)),
                    "type": parameter_type,
                    "values_by_one_based_case": {
                        str(case_index + 1): _safe(
                            lambda case_index=case_index, parameter_index=parameter_index:
                            table.GetValue(case_index, parameter_index)
                        )
                        for case_index in range(int(table.NumCases()))
                    },
                }
                parameters.append(parameter)
                if parameter_type == "Equation":
                    equations.append(_equation_record(table, parameter_index))
            studies.append(
                {
                    "index": study_index,
                    "name": str(study.GetName()),
                    "num_cases": int(table.NumCases()),
                    "parameters": parameters,
                    "equations": equations,
                    "result_file_names": _safe(study.GetResultFileNames),
                    "result_methods": sorted(
                        name
                        for name in dir(study)
                        if "Result" in name or "Response" in name or "Export" in name
                    ),
                }
            )
        return {
            "project": str(project),
            "model": str(model.GetName()),
            "num_studies": int(model.NumStudies()),
            "studies": studies,
        }
    finally:
        app.Quit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    inventory = probe(args.project.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(args.output.resolve())


if __name__ == "__main__":
    main()
