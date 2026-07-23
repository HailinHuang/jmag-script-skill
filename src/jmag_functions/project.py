"""Safe JMAG project loading and protected-copy ownership."""

from __future__ import annotations

from dataclasses import dataclass
import ctypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Self


DEFAULT_DESIGNER_EXECUTABLE = Path(r"C:\Program Files\JMAG-Designer25.1\designer.exe")
JMAG_VERSION = "25.1"


@dataclass(frozen=True)
class ProjectBundle:
    """A project file and its optional sibling result directory."""

    project_path: Path
    result_directory: Path
    has_result_directory: bool


class ProjectBundleCopyError(OSError):
    """A filesystem copy failure whose partial-target cleanup was attempted."""

    def __init__(self, message: str, *, cleanup_status: str) -> None:
        super().__init__(message)
        self.cleanup_status = cleanup_status


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validated_bundle_paths(source: str | Path, target: str | Path) -> tuple[Path, Path, Path, Path]:
    source_path = Path(source).resolve()
    target_path = Path(target).resolve()
    source_files = source_path.with_suffix(".jfiles")
    target_files = target_path.with_suffix(".jfiles")
    if source_path.suffix.lower() != ".jproj":
        raise ValueError("source must be a .jproj file")
    if target_path.suffix.lower() != ".jproj":
        raise ValueError("target must be a .jproj file")
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if source_path == target_path:
        raise ValueError("target must not overwrite the source project")
    if target_path.exists():
        raise FileExistsError(target_path)
    if target_files.exists():
        raise FileExistsError(target_files)
    if not target_path.parent.is_dir():
        raise FileNotFoundError(target_path.parent)
    if source_files.exists() and not source_files.is_dir():
        raise ValueError(f"source sibling is not a directory: {source_files}")
    return source_path, target_path, source_files, target_files


def _prepare_manifest_path(manifest_path: str | Path | None) -> Path | None:
    if manifest_path is None:
        return None
    path = Path(manifest_path).resolve()
    if path.exists():
        raise FileExistsError(path)
    if not path.parent.is_dir():
        raise FileNotFoundError(path.parent)
    return path


def _write_failed_manifest(
    manifest_path: Path | None,
    source: str | Path,
    target: str | Path,
    *,
    visible: bool,
    owns_application: bool,
    error: Exception,
) -> None:
    """Write one safe failure record before a managed session can exist."""
    if manifest_path is None:
        return
    source_path = Path(source).resolve()
    target_path = Path(target).resolve()
    source_files = source_path.with_suffix(".jfiles")
    target_files = target_path.with_suffix(".jfiles")
    cleanup_status = getattr(error, "cleanup_status", "not required")
    record = {
        "schema_version": 1,
        "operation": "protected_project_copy",
        "status": "failed",
        "source_project": str(source_path),
        "target_project": str(target_path),
        "source_bundle_has_jfiles": source_files.is_dir(),
        "target_bundle_has_jfiles": target_files.is_dir(),
        "source_project_sha256_before": _sha256(source_path) if source_path.is_file() else None,
        "source_project_sha256_after": _sha256(source_path) if source_path.is_file() else None,
        "target_project_sha256": _sha256(target_path) if target_path.is_file() else None,
        "jmag_version": JMAG_VERSION,
        "visible": visible,
        "study": None,
        "owns_application": owns_application,
        "started_at": _iso_now(),
        "completed_at": _iso_now(),
        "error": f"{type(error).__name__}: {error}; cleanup={cleanup_status}",
    }
    manifest_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _cleanup_partial_target(project_path: Path, result_directory: Path) -> str:
    errors: list[str] = []
    if result_directory.exists():
        try:
            if result_directory.is_dir():
                shutil.rmtree(result_directory)
            else:
                result_directory.unlink()
        except OSError as error:
            errors.append(f"{type(error).__name__}: {error}")
    if project_path.exists():
        try:
            project_path.unlink()
        except OSError as error:
            errors.append(f"{type(error).__name__}: {error}")
    return "completed" if not errors else "failed (" + "; ".join(errors) + ")"


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
class ManagedProjectSession:
    """A protected-copy project session with explicit application ownership."""

    app: Any
    source_bundle: ProjectBundle
    working_bundle: ProjectBundle
    owns_application: bool
    visible: bool
    selected_study: str | int | None
    manifest_path: Path | None
    source_project_sha256_before: str
    started_at: str
    _closed: bool = False
    _status: str = "created"
    _error: str | None = None

    @property
    def source(self) -> Path:
        """Compatibility alias for the source project path."""
        return self.source_bundle.project_path

    @property
    def copy(self) -> Path:
        """Compatibility alias for the protected working project path."""
        return self.working_bundle.project_path

    def _manifest_record(self) -> dict[str, object]:
        source_path = self.source_bundle.project_path
        target_path = self.working_bundle.project_path
        return {
            "schema_version": 1,
            "operation": "protected_project_copy",
            "status": self._status,
            "source_project": str(source_path),
            "target_project": str(target_path),
            "source_bundle_has_jfiles": self.source_bundle.has_result_directory,
            "target_bundle_has_jfiles": self.working_bundle.result_directory.is_dir(),
            "source_project_sha256_before": self.source_project_sha256_before,
            "source_project_sha256_after": _sha256(source_path),
            "target_project_sha256": _sha256(target_path) if target_path.is_file() else None,
            "jmag_version": JMAG_VERSION,
            "visible": self.visible,
            "study": self.selected_study,
            "owns_application": self.owns_application,
            "started_at": self.started_at,
            "completed_at": _iso_now() if self._closed else None,
            "error": self._error,
        }

    def _write_manifest(self) -> None:
        if self.manifest_path is None:
            return
        # The path was verified empty before the session started. Subsequent
        # writes are controlled updates of this session's own audit record.
        self.manifest_path.write_text(
            json.dumps(self._manifest_record(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _mark_failed(self, error: Exception) -> None:
        self._status = "failed"
        self._error = f"{type(error).__name__}: {error}"
        self._write_manifest()

    def _load_working_copy(self) -> None:
        load_project(self.app, self.working_bundle.project_path, study=self.selected_study)
        self._status = "loaded"
        self._write_manifest()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("ManagedProjectSession is closed")

    def select_study(self, study: str | int) -> Any:
        self._ensure_open()
        selected = select_study(self.app, study)
        self.selected_study = study
        self._write_manifest()
        return selected

    def save(self) -> None:
        self._ensure_open()
        try:
            save_project(self.app)
        except Exception as error:
            self._mark_failed(error)
            raise
        self._status = "saved"
        self._write_manifest()

    def close(self, *, save: bool = False) -> None:
        if not isinstance(save, bool):
            raise TypeError("save must be a boolean")
        if self._closed:
            return
        if save:
            self.save()
        if self.owns_application:
            self.app.Quit()
        self._closed = True
        if self._status != "failed":
            self._status = "closed"
        self._write_manifest()

    def __enter__(self) -> Self:
        self._ensure_open()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


# Kept as an import-compatible name for callers of the former API.
LoadedProject = ManagedProjectSession


def _new_session(
    app: Any,
    source_path: Path,
    target_bundle: ProjectBundle,
    *,
    owns_application: bool,
    visible: bool,
    study: str | int | None,
    manifest_path: Path | None,
) -> ManagedProjectSession:
    source_files = source_path.with_suffix(".jfiles")
    return ManagedProjectSession(
        app=app,
        source_bundle=ProjectBundle(source_path, source_files, source_files.is_dir()),
        working_bundle=target_bundle,
        owns_application=owns_application,
        visible=visible,
        selected_study=study,
        manifest_path=manifest_path,
        source_project_sha256_before=_sha256(source_path),
        started_at=_iso_now(),
    )


def _open_protected_project_copy(
    app: Any,
    source_path: Path,
    target_bundle: ProjectBundle,
    *,
    owns_application: bool,
    visible: bool,
    study: str | int | None,
    manifest_path: Path | None,
) -> ManagedProjectSession:
    session = _new_session(
        app,
        source_path,
        target_bundle,
        owns_application=owns_application,
        visible=visible,
        study=study,
        manifest_path=manifest_path,
    )
    session._write_manifest()
    try:
        session._load_working_copy()
    except Exception as error:
        session._mark_failed(error)
        session._closed = True
        session._write_manifest()
        raise
    return session


def open_protected_project_copy(
    source: str | Path,
    target: str | Path,
    *,
    visible: bool = False,
    study: str | int | None = None,
    manifest_path: str | Path | None = None,
) -> ManagedProjectSession:
    """Create, load, and own a filesystem-level protected project copy."""
    if not isinstance(visible, bool):
        raise TypeError("visible must be a boolean")
    prepared_manifest = _prepare_manifest_path(manifest_path)
    try:
        target_bundle = copy_project_bundle(source, target)
    except Exception as error:
        _write_failed_manifest(
            prepared_manifest, source, target, visible=visible,
            owns_application=True, error=error,
        )
        raise
    source_path = Path(source).resolve()
    try:
        app = create_application(visible=visible)
    except Exception as error:
        _write_failed_manifest(
            prepared_manifest, source, target, visible=visible,
            owns_application=True, error=error,
        )
        raise
    try:
        return _open_protected_project_copy(
            app,
            source_path,
            target_bundle,
            owns_application=True,
            visible=visible,
            study=study,
            manifest_path=prepared_manifest,
        )
    except Exception:
        # A copy/validation failure occurs before a managed session exists.
        # This application was explicitly created by this entry point.
        app.Quit()
        raise


def load_protected_project_copy(
    app: Any,
    source: str | Path,
    target: str | Path,
    *,
    study: str | int | None = None,
    manifest_path: str | Path | None = None,
) -> ManagedProjectSession:
    """Load a protected copy into a caller-owned application without quitting it."""
    if app is None:
        raise ValueError("app must be an explicit JMAG application")
    prepared_manifest = _prepare_manifest_path(manifest_path)
    try:
        target_bundle = copy_project_bundle(source, target)
    except Exception as error:
        _write_failed_manifest(
            prepared_manifest, source, target, visible=False,
            owns_application=False, error=error,
        )
        raise
    return _open_protected_project_copy(
        app,
        Path(source).resolve(),
        target_bundle,
        owns_application=False,
        visible=False,
        study=study,
        manifest_path=prepared_manifest,
    )


def load_project_copy(
    source: str | Path,
    target: str | Path,
    *,
    options: list[str] | None = None,
) -> ManagedProjectSession:
    """Compatibility wrapper for :func:`open_protected_project_copy`.

    It no longer loads the source and calls ``SaveAs``.  The only copy
    semantics are the canonical filesystem-level project-bundle copy.
    """
    if options not in (None, [], ["-g"]):
        raise ValueError("legacy options must be [] or ['-g']")
    return open_protected_project_copy(source, target, visible=options == [])


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


def copy_project_bundle(source: str | Path, target: str | Path) -> ProjectBundle:
    """Copy a JMAG project bundle through the filesystem, never ``SaveAs``.

    Targets must be absent. If copying either bundle member fails, this
    function removes only the target paths it just created and reports whether
    that cleanup completed. The source bundle is never modified or removed.
    """
    source_path, target_path, source_files, target_files = _validated_bundle_paths(source, target)
    has_result_directory = source_files.is_dir()
    try:
        shutil.copy2(source_path, target_path)
        if has_result_directory:
            shutil.copytree(source_files, target_files)
    except Exception as error:
        cleanup_status = _cleanup_partial_target(target_path, target_files)
        raise ProjectBundleCopyError(
            f"protected project bundle copy failed: {type(error).__name__}: {error}; "
            f"partial-target cleanup={cleanup_status}",
            cleanup_status=cleanup_status,
        ) from error
    return ProjectBundle(
        project_path=target_path,
        result_directory=target_files,
        has_result_directory=has_result_directory,
    )


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
