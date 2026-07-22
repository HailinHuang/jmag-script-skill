"""Explicit orchestration composed from the core JMAG functions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .design_table import set_parameters
from .results import get_values
from .session import JMAGContext
from .study import run_cases


def _case_numbers(
    context: JMAGContext, cases: int | Iterable[int]
) -> list[int]:
    if isinstance(cases, bool):
        raise TypeError("cases must be a 1-based integer or an iterable of integers")
    if isinstance(cases, int):
        values = [cases]
    else:
        if isinstance(cases, (str, bytes)):
            raise TypeError(
                "cases must be a 1-based integer or an iterable of integers"
            )
        values = list(cases)
    if not values:
        raise ValueError("cases must not be empty")
    for case in values:
        context.case_index(case)
    if len(set(values)) != len(values):
        raise ValueError("cases must not contain duplicates")
    return values


def _value_names(names: Iterable[str]) -> list[str]:
    if isinstance(names, (str, bytes)):
        raise TypeError("names must be an iterable of names, not a string")
    values = list(names)
    if not values:
        raise ValueError("names must not be empty")
    if any(not isinstance(name, str) or not name for name in values):
        raise TypeError("every name must be a non-empty string")
    if len(set(values)) != len(values):
        raise ValueError("names must not contain duplicates")
    return values


def evaluate_cases(
    context: JMAGContext,
    parameter_values: Mapping[str, Any],
    names: Iterable[str],
    cases: int | Iterable[int],
    *,
    clear_results: bool,
) -> dict[int, dict[str, Any]]:
    """Set parameters, run requested cases, and return scalar values by case.

    Public case numbers are one-based. ``clear_results`` has no default so
    callers must explicitly choose the destructive result-clearing policy.
    Project paths, study names, response names, and machine constants remain
    outside this reusable function.
    """
    if not isinstance(parameter_values, Mapping):
        raise TypeError("parameter_values must be a mapping")
    if not isinstance(clear_results, bool):
        raise TypeError("clear_results must be a boolean")
    case_numbers = _case_numbers(context, cases)
    value_names = _value_names(names)

    # Resolve every parameter before the first write, including an empty map.
    if not parameter_values:
        raise ValueError("parameter_values must not be empty")
    for name in parameter_values:
        context.parameter_index(name)

    for case in case_numbers:
        set_parameters(context, parameter_values, case)
    run_cases(
        context,
        case_numbers,
        clear_results=clear_results,
        apply_cad_parameters=True,
    )
    return {
        case: get_values(context, value_names, case)
        for case in case_numbers
    }
