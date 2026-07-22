"""Run all or selected JMAG cases with explicit result-clearing policy."""

from __future__ import annotations

from collections.abc import Iterable

from .session import JMAGContext


def _normalize_cases(context: JMAGContext, cases: int | Iterable[int]) -> list[int]:
    values = [cases] if isinstance(cases, int) and not isinstance(cases, bool) else list(cases)
    if not values:
        raise ValueError("cases must not be empty")
    indexes = [context.case_index(case) for case in values]
    if len(set(indexes)) != len(indexes):
        raise ValueError("cases must not contain duplicates")
    return indexes


def run_cases(
    context: JMAGContext,
    cases: int | Iterable[int] | None = None,
    clear_results: bool = True,
    *,
    apply_cad_parameters: bool = False,
) -> None:
    if not isinstance(clear_results, bool):
        raise TypeError("clear_results must be a boolean")
    if not isinstance(apply_cad_parameters, bool):
        raise TypeError("apply_cad_parameters must be a boolean")
    indexes = None if cases is None else _normalize_cases(context, cases)
    context.activate()
    if apply_cad_parameters:
        context.study.ApplyAllCasesCadParameters()
    if clear_results and hasattr(context.study, "DeleteResult"):
        context.study.DeleteResult()
    if cases is None:
        context.study.RunAllCases()
        return
    original = context.study.GetCurrentCase()
    try:
        for index in indexes:
            context.study.SetCurrentCase(index)
            context.study.Run()
    finally:
        context.study.SetCurrentCase(original)
