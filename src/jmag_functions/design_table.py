"""Write JMAG design-table equation parameters without hidden result deletion."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .session import JMAGContext


def set_parameter(context: JMAGContext, name: str, value: Any, case: int = 1) -> None:
    set_parameters(context, {name: value}, case)


def set_parameters(context: JMAGContext, values: Mapping[str, Any], case: int = 1) -> None:
    if not values:
        raise ValueError("values must not be empty")
    case_index = context.case_index(case)
    # Resolve every name before the first write, preventing partial updates.
    resolved = [(context.parameter_index(name), value) for name, value in values.items()]
    context.activate()
    for parameter_index, value in resolved:
        context.table.SetValue(case_index, parameter_index, value)
