"""Open JMAG visibly, with optional handling for missing result files.

The default path is intentionally fast: it validates the project path and
launches JMAG without parsing the project or scanning its result directory.
Use --handle-missing-results only when the project is expected to show JMAG's
"Missing Result Files" dialog.
"""

from __future__ import annotations

import argparse
import ctypes
from functools import lru_cache
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path


JPLOT_PATTERN = re.compile(rb"[A-Za-z0-9_./~ -]+\.jplot", re.IGNORECASE)
VALID_MODES = {"original", "copy", "copy-delete-original"}


@lru_cache(maxsize=1)
def _load_jmag_project_api() -> tuple[Path, object]:
    """Configure and import JMAG only when a launch is actually requested."""
    try:
        from ._jmag_user_env import configure_environment
    except ImportError:
        from _jmag_user_env import configure_environment

    configure_environment()
    from jmag_functions.project import (
        DEFAULT_DESIGNER_EXECUTABLE,
        launch_project_in_visible_designer,
    )

    return DEFAULT_DESIGNER_EXECUTABLE, launch_project_in_visible_designer


def find_missing_result_files(project: Path) -> list[str]:
    """Return missing .jplot references found in a JMAG project.

    This is an opt-in diagnostic because reading the project and walking a
    large .jfiles tree can noticeably delay startup.
    """
    project = project.resolve()
    data = project.read_bytes()
    references = {
        match.decode("utf-8", errors="ignore").replace("\\", "/")
        for match in JPLOT_PATTERN.findall(data)
    }
    result_root = project.with_suffix(".jfiles")

    if not result_root.is_dir():
        if references:
            return sorted(references)
        return ["*.jplot (.jfiles directory not found)"]

    # next(...) stops after the first match; list(rglob(...)) scans everything.
    if next(result_root.rglob("*.jplot"), None) is None:
        return ["*.jplot (no result files found in the .jfiles directory)"]

    missing: list[str] = []
    for reference in sorted(references):
        reference_path = Path(reference)
        candidate = reference_path if reference_path.is_absolute() else result_root / reference_path
        if not candidate.is_file():
            missing.append(reference)
    return missing


def copy_project_bundle(source: Path, target: Path) -> Path:
    """Copy a .jproj and its sibling .jfiles directory without overwriting."""
    source = source.resolve()
    target = target.resolve()
    target_files = target.with_suffix(".jfiles")
    if target.exists() or target_files.exists():
        raise FileExistsError(f"copy target already exists: {target}")
    if not target.parent.is_dir():
        raise FileNotFoundError(target.parent)

    shutil.copy2(source, target)
    source_files = source.with_suffix(".jfiles")
    if source_files.is_dir():
        shutil.copytree(source_files, target_files)
    return target


def _find_missing_result_dialog() -> int:
    """Find JMAG's missing-result dialog using the lightweight Win32 API."""
    if not hasattr(ctypes, "windll"):
        return 0

    user32 = ctypes.windll.user32
    handles: list[int] = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    @callback_type
    def enum_callback(hwnd: int, _lparam: int) -> bool:
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            if "Missing Result Files" in buffer.value:
                handles.append(hwnd)
                return False
        return True

    user32.EnumWindows(enum_callback, 0)
    return handles[0] if handles else 0


def dismiss_missing_result_dialog(
    timeout: float = 15.0,
    stop_event: threading.Event | None = None,
) -> bool:
    """Confirm JMAG's missing-result dialog using Win32 only.

    Avoiding UI Automation/pywinauto makes each poll substantially cheaper.
    The dialog title may include a JMAG prefix; enumeration uses a substring.
    """
    stop_event = stop_event or threading.Event()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and not stop_event.is_set():
        dialog = _find_missing_result_dialog()
        if dialog:
            user32 = ctypes.windll.user32
            ok_button = user32.GetDlgItem(dialog, 1)  # Win32 IDOK
            if not ok_button:
                ok_button = user32.FindWindowExW(dialog, 0, "Button", "OK")
            if ok_button:
                user32.SendMessageW(ok_button, 0x00F5, 0, 0)  # BM_CLICK
                print("Missing-result dialog confirmed automatically.")
                return True
        stop_event.wait(0.25)
    return False


def _wait_for_jmag_context(timeout: float, project: Path) -> None:
    """Wait until JMAG exposes a current model/study automation context."""
    _load_jmag_project_api()
    from jmag_functions.session import JMAGContext

    deadline = time.monotonic() + timeout
    while True:
        try:
            JMAGContext.from_current()
            print(f"JMAG is open: {project}")
            return
        except Exception as error:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "JMAG model/study was not available before timeout"
                ) from error
            time.sleep(0.5)


def open_jmag_window(
    project: Path | None = None,
    timeout: float = 30.0,
    *,
    mode: str = "original",
    copy_target: Path | None = None,
    confirm_delete_original: bool = False,
    attach: bool = False,
    handle_missing_results: bool = False,
    dialog_timeout: float = 15.0,
) -> None:
    """Launch JMAG using ``original``, ``copy`` or ``copy-delete-original``.

    Normal ``original`` mode does not inspect result files. Result inspection
    is enabled by ``handle_missing_results`` and is forced for the destructive
    ``copy-delete-original`` mode.
    """
    if project is None:
        if mode != "original":
            raise ValueError("a project path is required for copy modes")
        designer_executable, _launch_project = _load_jmag_project_api()
        subprocess.Popen([str(designer_executable)])
        print("JMAG Designer launched without loading a project.")
        return

    if mode not in VALID_MODES:
        raise ValueError(f"unsupported mode: {mode}")

    project = project.resolve()
    if not project.is_file():
        raise FileNotFoundError(project)

    if mode == "copy-delete-original" and not confirm_delete_original:
        raise ValueError("copy-delete-original requires --confirm-delete-original")

    launch_project = project
    if mode != "original":
        launch_project = copy_target or project.with_name(
            project.stem + "_automation_copy.jproj"
        )
        copy_project_bundle(project, launch_project)
        print(f"Opening project copy: {launch_project}")

    # Destructive mode always checks first; normal/copy modes check only on request.
    inspect_results = handle_missing_results or mode == "copy-delete-original"
    missing = find_missing_result_files(launch_project) if inspect_results else []
    if missing:
        print("WARNING: result files are missing:")
        for reference in missing:
            print(f"  Missing result file: {reference}")

    # Start the watcher before launching. This also handles launch helpers that
    # block while JMAG is waiting for the modal dialog to be acknowledged.
    dialog_confirmed = threading.Event()
    stop_watcher = threading.Event()
    watcher: threading.Thread | None = None
    if missing:
        def watch_dialog() -> None:
            if dismiss_missing_result_dialog(dialog_timeout, stop_watcher):
                dialog_confirmed.set()

        watcher = threading.Thread(target=watch_dialog, daemon=True)
        watcher.start()

    _designer_executable, launch_project_in_visible_designer = _load_jmag_project_api()
    launch_project_in_visible_designer(launch_project)

    if watcher is not None:
        watcher.join(dialog_timeout)
        stop_watcher.set()

    if mode == "copy-delete-original":
        if missing and not dialog_confirmed.is_set():
            raise RuntimeError(
                "Original was not deleted because the missing-result dialog "
                "could not be confirmed automatically."
            )
        source_files = project.with_suffix(".jfiles")
        if source_files.is_dir():
            shutil.rmtree(source_files)
        project.unlink()
        print(f"Deleted original project bundle: {project}")

    if attach:
        _wait_for_jmag_context(timeout, launch_project)
    else:
        print(f"JMAG launch requested: {launch_project}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Open JMAG visibly; result checks are opt-in for fast startup."
    )
    parser.add_argument("project", type=Path, nargs="?", default=None)
    parser.add_argument(
        "--mode",
        choices=("original", "copy", "copy-delete-original"),
        default="original",
    )
    parser.add_argument("--copy-target", type=Path)
    parser.add_argument("--confirm-delete-original", action="store_true")
    parser.add_argument(
        "--handle-missing-results",
        action="store_true",
        help="scan result files and automatically confirm JMAG's warning dialog",
    )
    parser.add_argument(
        "--dialog-timeout",
        type=float,
        default=15.0,
        help="seconds to wait for the missing-result dialog (default: 15)",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--attach", action="store_true")
    args = parser.parse_args()

    open_jmag_window(
        args.project,
        args.timeout,
        mode=args.mode,
        copy_target=args.copy_target,
        confirm_delete_original=args.confirm_delete_original,
        attach=args.attach,
        handle_missing_results=args.handle_missing_results,
        dialog_timeout=args.dialog_timeout,
    )


if __name__ == "__main__":
    main()
