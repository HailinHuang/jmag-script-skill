"""Read scalar equation parameters and response values."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .session import JMAGContext


def get_value(context: JMAGContext, name: str, case: int = 1) -> Any:
    index = context.case_index(case)
    context.activate()
    if context.has_parameter(name):
        return context.table.GetEquation(name).GetValue(index)
    response = context.study.GetResponseData(name, index)
    if response is None or len(response) == 0:
        raise KeyError(f"JMAG value not found: {name!r} for case {case}")
    if len(response) != 1:
        raise ValueError(f"Expected one scalar for {name!r}; got {len(response)} values")
    return response[0]


def get_values(context: JMAGContext, names: Iterable[str], case: int = 1) -> dict[str, Any]:
    if isinstance(names, (str, bytes)):
        raise TypeError("names must be an iterable of names, not a string")
    materialized = list(names)
    if len(set(materialized)) != len(materialized):
        raise ValueError("names must not contain duplicates")
    return {name: get_value(context, name, case) for name in materialized}
