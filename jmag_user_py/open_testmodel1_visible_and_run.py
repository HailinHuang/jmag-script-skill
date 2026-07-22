"""Open TestModel1 in visible JMAG Designer and run its current study."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

try:
    from ._jmag_user_env import configure_environment
except ImportError:
    from _jmag_user_env import configure_environment

configure_environment()

from jmag_functions import JMAGContext, run_cases
from jmag_functions.project import launch_project_in_visible_designer


PROJECT = Path(r"C:\JMAG_Models\TestModel1.jproj")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Open TestModel1 visibly and run its current study."
    )
    parser.add_argument("--project", type=Path, default=PROJECT)
    parser.add_argument(
        "--run",
        action="store_true",
        help="start the current study after opening the project",
    )
    args = parser.parse_args()
    if not args.run:
        print("Validation only. Pass --run to open the project and start its study.")
        return

    launch_project_in_visible_designer(args.project)
    deadline = time.monotonic() + 30
    while True:
        try:
            context = JMAGContext.from_current()
            break
        except RuntimeError:
            if time.monotonic() >= deadline:
                raise RuntimeError("JMAG Designer did not expose a current study within 30 seconds")
            time.sleep(1)
    run_cases(context, clear_results=False)
    print("Current study started for all cases.")
    print("JMAG Designer remains open; close it manually when finished.")


if __name__ == "__main__":
    main()
