"""Safe JMAG project loading and protected-copy ownership."""

from __future__ import annotations

from dataclasses import dataclass
import ctypes
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Self


DEFAULT_DESIGNER_EXECUTABLE = Path(r"C:\Program Files\JMAG-Designer25.1\designer.exe")


def _create_application(options: list[str]) -> Any:
    from jmag.designer import designer
    return designer.CreateApplication(options)


def create_application(*, visible: bool = False) -> Any:
    """Create a JMAG Designer application with explicit window visibility."""
    if not isinstance(visible, bool):
        raise TypeError("visible must be a boolean")

    return _create_application([] if visible else ["-g"])


def select_study(app: Any, study: str | int) -> Any:
    """Select and return a study in the current model."""
    model = app.GetCurrentModel()
    if model is None:
        raise RuntimeError("No current JMAG model is available")
    selected_study = model.GetStudy(study)
    if selected_study is None:
        raise RuntimeError(f"JMAG study not found: {study!r}")
    app.SetStudyAsCurrent(selected_study)
    return selected_study


def load_project(app: Any, source: str | Path, *, study: str | int | None = None) -> Any:
    """Load a project into ``app`` and optionally select one of its studies."""
    source_path = Path(source).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    app.Load(str(source_path))
    if study is None:
        return app

    select_study(app, study)
    return app


def save_project(app: Any) -> None:
    """Save the project currently loaded in ``app``."""
    app.Save()


def save_project_as(app: Any, target: str | Path, *, overwrite: bool = False) -> Path:
    """Save the current project to a new path, rejecting overwrite by default."""
    if not isinstance(overwrite, bool):
        raise TypeError("overwrite must be a boolean")
    target_path = Path(target).resolve()
    if target_path.exists() and not overwrite:
        raise FileExistsError(target_path)
    if not target_path.parent.is_dir():
        raise FileNotFoundError(target_path.parent)
    app.SaveAs(str(target_path))
    return target_path


def close_application(app: Any, *, save: bool = False) -> None:
    """Close JMAG, optionally saving first; default behavior never saves."""
    if not isinstance(save, bool):
        raise TypeError("save must be a boolean")
    if save:
        save_project(app)
    app.Quit()


@dataclass
class ProjectSession:
    """Own one JMAG application and provide a conventional project session API."""

    app: Any
    _closed: bool = False

    @classmethod
    def open(
        cls,
        source: str | Path,
        *,
        visible: bool = True,
        study: str | int | None = None,
    ) -> Self:
        return cls(open_project(source, visible=visible, study=study))

    def load(self, source: str | Path, *, study: str | int | None = None) -> Any:
        self._ensure_open()
        return load_project(self.app, source, study=study)

    def select_study(self, study: str | int) -> Any:
        self._ensure_open()
        return select_study(self.app, study)

    def save(self) -> None:
        self._ensure_open()
        save_project(self.app)

    def save_as(self, target: str | Path, *, overwrite: bool = False) -> Path:
        self._ensure_open()
        return save_project_as(self.app, target, overwrite=overwrite)

    def close(self, *, save: bool = False) -> None:
        if self._closed:
            return
        close_application(self.app, save=save)
        self._closed = True

    def __enter__(self) -> Self:
        self._ensure_open()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("ProjectSession is closed")


@dataclass
class LoadedProject:
    """A loaded project whose application lifecycle is explicit."""

    app: Any
    source: Path
    copy: Path
    owns_application: bool = False
    _closed: bool = False

    def save(self) -> None:
        if self._closed:
            raise RuntimeError("LoadedProject is closed")
        self.app.Save()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.owns_application:
            self.app.Quit()

    def __enter__(self) -> Self:
        if self._closed:
            raise RuntimeError("LoadedProject is closed")
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


def load_project_copy(
    source: str | Path,
    target: str | Path,
    *,
    options: list[str] | None = None,
) -> LoadedProject:
    """Load ``source`` and immediately save it to a new protected copy.

    Existing targets are rejected. The function always creates and owns a new
    application so it cannot replace a caller's current project or discard
    unsaved state in a borrowed application.
    """
    source_path = Path(source).resolve()
    target_path = Path(target).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if source_path == target_path:
        raise ValueError("target must not overwrite the source project")
    if target_path.exists():
        raise FileExistsError(target_path)
    if not target_path.parent.is_dir():
        raise FileNotFoundError(target_path.parent)

    app = create_application(visible=False) if options is None else _create_application(options)
    try:
        app.Load(str(source_path))
        app.SaveAs(str(target_path))
    except Exception:
        app.Quit()
        raise
    return LoadedProject(
        app=app,
        source=source_path,
        copy=target_path,
        owns_application=True,
    )


def open_project_visible(source: str | Path, *, study: str | int | None = None) -> Any:
    """Open a JMAG project in a visible Designer instance without owning it.

    The caller controls the returned application lifecycle.  This deliberately
    avoids the ``-g`` option used by batch scripts and never calls ``Quit()``.
    """
    return open_project(source, visible=True, study=study)


def open_project(
    source: str | Path,
    *,
    visible: bool = True,
    study: str | int | None = None,
) -> Any:
    """Create a JMAG application, load a project, and optionally select a study."""
    app = create_application(visible=visible)
    try:
        load_project(app, source, study=study)
    except Exception:
        close_application(app)
        raise
    return app


def launch_project_in_visible_designer(
    source: str | Path,
    *,
    designer_executable: str | Path = DEFAULT_DESIGNER_EXECUTABLE,
) -> subprocess.Popen[Any]:
    """Launch a project in JMAG Designer's visible desktop application."""
    source_path = Path(source).resolve()
    executable_path = Path(designer_executable)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if not executable_path.is_file():
        raise FileNotFoundError(executable_path)
    return subprocess.Popen([str(executable_path), str(source_path)])


def find_missing_result_files(project: str | Path) -> list[str]:
    """Preflight a project for readable missing ``.jplot`` result references."""
    project_path = Path(project).resolve()
    if not project_path.is_file():
        raise FileNotFoundError(project_path)
    references = {
        match.decode("utf-8", errors="ignore").replace("\\", "/")
        for match in re.findall(
            rb"[A-Za-z0-9_./~ -]+\.jplot", project_path.read_bytes(), re.IGNORECASE
        )
    }
    result_root = project_path.with_suffix(".jfiles")
    if result_root.is_dir() and not list(result_root.rglob("*.jplot")):
        return ["*.jplot (no result files found in the .jfiles directory)"]
    return [
        reference
        for reference in sorted(references)
        if not (result_root / Path(reference)).is_file()
    ]


def copy_project_bundle(source: str | Path, target: str | Path) -> Path:
    """Copy a ``.jproj`` and sibling ``.jfiles`` directory without overwrite."""
    source_path = Path(source).resolve()
    target_path = Path(target).resolve()
    target_files = target_path.with_suffix(".jfiles")
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if target_path.exists() or target_files.exists():
        raise FileExistsError(f"copy target already exists: {target_path}")
    if not target_path.parent.is_dir():
        raise FileNotFoundError(target_path.parent)
    shutil.copy2(source_path, target_path)
    source_files = source_path.with_suffix(".jfiles")
    if source_files.is_dir():
        shutil.copytree(source_files, target_files)
    return target_path


def dismiss_missing_result_dialog(timeout: float = 30.0) -> bool:
    """Confirm JMAG's missing-result dialog using UI Automation or Win32."""
    try:
        from pywinauto import Desktop
    except ImportError:
        Desktop = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if Desktop is not None:
                dialog = Desktop(backend="uia").window(title_re=".*Missing Result Files.*")
                if dialog.exists(timeout=0.2):
                    dialog.child_window(title="OK", control_type="Button").click_input()
                    return True
            user32 = ctypes.windll.user32
            dialog_handle = user32.FindWindowW(None, "JMAG-Designer: Missing Result Files")
            if not dialog_handle:
                dialog_handle = user32.FindWindowW(None, "Missing Result Files")
            if dialog_handle:
                ok_handle = user32.FindWindowExW(dialog_handle, None, "Button", "OK")
                if ok_handle:
                    user32.SendMessageW(ok_handle, 0x00F5, 0, 0)  # BM_CLICK
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def open_jmag_fast(
    project: str | Path | None = None,
    *,
    mode: str = "original",
    copy_target: str | Path | None = None,
    timeout: float = 30.0,
    confirm_delete_original: bool = False,
    attach: bool = False,
    designer_executable: str | Path = DEFAULT_DESIGNER_EXECUTABLE,
) -> subprocess.Popen[Any]:
    """Open a project with missing-result preflight and explicit copy policy.

    ``mode`` is ``original`` (preserve source), ``copy`` (open a protected
    sibling copy), or ``copy-delete-original`` (requires explicit confirmation).
    When missing results are detected, the function attempts to confirm JMAG's
    dialog automatically. The source is never deleted unless the last mode and
    ``confirm_delete_original=True`` are both selected.
    """
    if mode not in {"original", "copy", "copy-delete-original"}:
        raise ValueError(f"unsupported mode: {mode}")
    if project is None:
        if mode != "original":
            raise ValueError("a project path is required for copy modes")
        executable_path = Path(designer_executable)
        if not executable_path.is_file():
            raise FileNotFoundError(executable_path)
        return subprocess.Popen([str(executable_path)])
    project_path = Path(project).resolve()
    if not project_path.is_file():
        raise FileNotFoundError(project_path)
    missing = find_missing_result_files(project_path)
    launch_path = project_path
    if mode != "original":
        if mode == "copy-delete-original" and not confirm_delete_original:
            raise ValueError("copy-delete-original requires confirm_delete_original=True")
        launch_path = Path(copy_target).resolve() if copy_target is not None else project_path.with_name(
            project_path.stem + "_automation_copy.jproj"
        )
        copy_project_bundle(project_path, launch_path)
    process = launch_project_in_visible_designer(
        launch_path, designer_executable=designer_executable
    )
    dialog_confirmed = not missing or dismiss_missing_result_dialog(timeout)
    if mode == "copy-delete-original":
        if not dialog_confirmed:
            raise RuntimeError("missing-result dialog could not be confirmed; original preserved")
        source_files = project_path.with_suffix(".jfiles")
        if source_files.is_dir():
            shutil.rmtree(source_files)
        project_path.unlink()
    if attach:
        from .session import JMAGContext

        deadline = time.monotonic() + timeout
        while True:
            try:
                JMAGContext.from_current()
                break
            except Exception as error:
                if time.monotonic() >= deadline:
                    raise TimeoutError("JMAG model/study was not available before timeout") from error
                time.sleep(1)
    return process
