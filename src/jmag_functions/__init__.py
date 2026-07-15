"""Stable, project-independent JMAG functions."""

from .session import JMAGContext
from .design_table import set_parameter, set_parameters
from .results import get_value, get_values
from .study import run_cases
from ._version import __version__

__all__ = [
    "JMAGContext", "get_value", "get_values", "set_parameter",
    "set_parameters", "run_cases", "__version__",
]
