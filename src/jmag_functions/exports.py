"""Explicit file exports for JMAG Design Tables and solver results."""

from __future__ import annotations

from pathlib import Path

from .session import JMAGContext


_TABLE_SUFFIXES = {".csv", ".txt", ".htm", ".html"}
_RESULT_AXES = {"Step", "Time", "Angle", "Distance"}


def _output_path(path: str | Path, *, overwrite: bool) -> Path:
    output = Path(path).resolve()
    if output.suffix.lower() not in _TABLE_SUFFIXES:
        raise ValueError("output must use .csv, .txt, .htm, or .html")
    if not output.parent.is_dir():
        raise FileNotFoundError(output.parent)
    if output.exists() and not overwrite:
        raise FileExistsError(output)
    return output


def export_design_table(
    context: JMAGContext, path: str | Path, *, overwrite: bool = False
) -> Path:
    output = _output_path(path, overwrite=overwrite)
    context.activate()
    context.table.Export(str(output))
    return output


def export_case_values(
    context: JMAGContext, path: str | Path, *, overwrite: bool = False
) -> Path:
    output = _output_path(path, overwrite=overwrite)
    context.activate()
    context.study.ExportCaseValueData(str(output))
    return output


def export_result_tables(
    context: JMAGContext,
    path: str | Path,
    *,
    axis: str,
    overwrite: bool = False,
) -> Path:
    if axis not in _RESULT_AXES:
        choices = ", ".join(sorted(_RESULT_AXES))
        raise ValueError(f"axis must be one of: {choices}")
    output = _output_path(path, overwrite=overwrite)
    context.activate()
    context.study.GetResultTable().WriteAllCaseTables(str(output), axis)
    return output
