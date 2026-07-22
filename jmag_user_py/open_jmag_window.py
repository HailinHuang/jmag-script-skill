"""Thin user-facing wrapper for the reusable JMAG fast-open function."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from ._jmag_user_env import configure_environment
except ImportError:
    from _jmag_user_env import configure_environment

configure_environment()

from jmag_functions import open_jmag_fast


open_jmag_fast(
    r"C:\JMAG_Models\motor.jproj",
    mode="original",
)