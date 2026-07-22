"""Configure imports for standalone scripts run with JMAG's bundled Python."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JMAG_INSTALLATION = Path(r"C:\Program Files\JMAG-Designer25.1")


def configure_environment() -> Path:
    """Make the package source and JMAG API modules importable from this folder."""
    for import_path in (ROOT / "src", JMAG_INSTALLATION):
        if str(import_path) not in sys.path:
            sys.path.insert(0, str(import_path))
    return ROOT
