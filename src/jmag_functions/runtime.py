"""Inspect and safely control running JMAG Designer and Scheduler activity."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import ctypes
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
from typing import Any, Iterable, Iterator, Mapping, Protocol, Sequence


_JPROJ_RE = re.compile(r"\"([^\"]+?\.jproj)\"|([^\s\"']+?\.jproj)(?=\s|$)", re.IGNORECASE)


@dataclass(frozen=True)
class ProcessRecord:
    """Read-only metadata for a process returned by the host OS."""

    name: str
    pid: int
    command_line: str = ""
    parent_pid: int | None = None
    executable_path: str = ""
    window_handle: int | None = None
    window_title: str = ""


@dataclass(frozen=True)
class RuntimeTarget:
    """A stable, inspectable JMAG runtime target."""

    target_id: str
    kind: str
    pid: int | None = None
    project_path: Path | None = None
    status: str = "unknown"
    progress: float | None = None
    window_handle: int | None = None
    attached: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeSnapshot:
    """The result of one read-only runtime inspection."""

    targets: tuple[RuntimeTarget, ...] = ()
    diagnostics: tuple[str, ...] = ()

    def by_kind(self, kind: str) -> list[RuntimeTarget]:
        return [target for target in self.targets if target.kind == kind]

    def get(self, target_id: str) -> RuntimeTarget | None:
        return next(
            (target for target in self.targets if target.target_id == target_id),
            None,
        )


@dataclass(frozen=True)
class OperationResult:
    """Outcome for one target; failures do not stop sibling targets."""

    target_id: str
    operation: str
    ok: bool
    message: str
    error: str | None = None


class ProcessProvider(Protocol):
    def records(self) -> Sequence[ProcessRecord]: ...


class WindowController(Protocol):
    def bring_to_front(self, handle: int) -> None: ...

    def minimize(self, handle: int) -> None: ...


class ProcessController(Protocol):
    def terminate(self, pid: int) -> None: ...


def _normalize_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    text = str(value).strip().strip('"')
    if not text:
        return None
    return Path(text).resolve()


def parse_jproj_path(command_line: str | None) -> Path | None:
    """Extract the first `.jproj` path from a Windows command line."""
    if not command_line:
        return None
    match = _JPROJ_RE.search(command_line)
    if not match:
        return None
    return _normalize_path(match.group(1) or match.group(2))


def process_records_from_rows(rows: Iterable[Mapping[str, Any]]) -> list[ProcessRecord]:
    """Convert PowerShell process rows into typed, read-only records."""
    records: list[ProcessRecord] = []
    for row in rows:
        name = str(row.get("Name") or "")
        if not name or row.get("ProcessId") is None:
            continue
        raw_handle = row.get("MainWindowHandle")
        records.append(
            ProcessRecord(
                name=name,
                pid=int(row["ProcessId"]),
                command_line=str(row.get("CommandLine") or ""),
                parent_pid=(
                    int(row["ParentProcessId"])
                    if row.get("ParentProcessId") is not None
                    else None
                ),
                executable_path=str(row.get("ExecutablePath") or ""),
                window_handle=(int(raw_handle) if raw_handle else None),
                window_title=str(row.get("MainWindowTitle") or ""),
            )
        )
    return records


def _same_path(left: Path | None, right: Path | None) -> bool:
    return left is not None and right is not None and os.path.normcase(str(left)) == os.path.normcase(str(right))


def merge_runtime_targets(
    attached: Sequence[RuntimeTarget],
    scheduler: Sequence[RuntimeTarget],
    processes: Sequence[ProcessRecord],
) -> list[RuntimeTarget]:
    """Merge API and OS observations while preserving attached capabilities."""
    merged: dict[str, RuntimeTarget] = {
        target.target_id: target for target in (*attached, *scheduler)
    }

    for process in processes:
        project_path = parse_jproj_path(process.command_line)
        matched_id = next(
            (
                target_id
                for target_id, target in merged.items()
                if (process.pid and target.pid == process.pid)
                or _same_path(target.project_path, project_path)
            ),
            None,
        )
        if matched_id is not None:
            target = merged[matched_id]
            merged[matched_id] = replace(
                target,
                pid=target.pid or process.pid,
                project_path=project_path or target.project_path,
                window_handle=target.window_handle or process.window_handle,
                metadata={
                    **dict(target.metadata),
                    "process_name": process.name,
                    "command_line": process.command_line,
                    "executable_path": process.executable_path,
                },
            )
            continue

        target_id = f"process:{process.pid}"
        merged[target_id] = RuntimeTarget(
            target_id=target_id,
            kind="process",
            pid=process.pid,
            project_path=project_path,
            status="running",
            window_handle=process.window_handle,
            metadata={
                "process_name": process.name,
                "command_line": process.command_line,
                "parent_pid": process.parent_pid,
                "executable_path": process.executable_path,
                "window_title": process.window_title,
            },
        )

    return sorted(merged.values(), key=lambda target: (target.kind, target.target_id))


class WindowsProcessProvider:
    """Discover JMAG processes without requiring a third-party dependency."""

    _SCRIPT = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -match '(?i)jmag|designer|scheduler' } | "
        "ForEach-Object { "
        "$window = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue; "
        "$handle = 0; $title = ''; "
        "if ($window) { $handle = $window.Handle; $title = $window.Title }; "
        "[pscustomobject]@{ Name=$_.Name; ProcessId=$_.ProcessId; "
        "CommandLine=$_.CommandLine; ParentProcessId=$_.ParentProcessId; "
        "ExecutablePath=$_.ExecutablePath; MainWindowHandle=$handle; "
        "MainWindowTitle=$title } } | "
        "ConvertTo-Json -Compress"
    )

    def records(self) -> list[ProcessRecord]:
        if os.name != "nt":
            return []
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", self._SCRIPT],
            check=True,
            capture_output=True,
            text=True,
        )
        if not completed.stdout.strip():
            return []
        payload = json.loads(completed.stdout)
        rows = payload if isinstance(payload, list) else [payload]
        return process_records_from_rows(rows)


class WindowsWindowController:
    """Small Windows-only window adapter; failures remain operation-local."""

    SW_MINIMIZE = 6

    def _user32(self) -> Any:
        if os.name != "nt":
            raise OSError("window control is available only on Windows")
        return ctypes.windll.user32

    def bring_to_front(self, handle: int) -> None:
        if not self._user32().SetForegroundWindow(int(handle)):
            raise OSError(f"SetForegroundWindow failed for handle {handle}")

    def minimize(self, handle: int) -> None:
        if not self._user32().ShowWindow(int(handle), self.SW_MINIMIZE):
            raise OSError(f"ShowWindow failed for handle {handle}")


class WindowsProcessController:
    def terminate(self, pid: int) -> None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                check=True,
                capture_output=True,
                text=True,
            )
            return
        os.kill(pid, signal.SIGTERM)


def _optional_call(obj: Any, name: str, default: Any = None) -> Any:
    method = getattr(obj, name, None)
    if not callable(method):
        return default
    try:
        return method()
    except Exception:
        return default


def _result(target_id: str, operation: str, ok: bool, message: str, error: Exception | None = None) -> OperationResult:
    return OperationResult(
        target_id=target_id,
        operation=operation,
        ok=ok,
        message=message,
        error=None if error is None else f"{type(error).__name__}: {error}",
    )


class JMAGRuntimeManager:
    """Inspect and control attached JMAG and host-level runtime targets."""

    def __init__(
        self,
        *,
        app: Any | None = None,
        scheduler: Any | None = None,
        scheduler_folders: Iterable[str | Path] = (),
        process_provider: ProcessProvider | None = None,
        window_controller: WindowController | None = None,
        process_controller: ProcessController | None = None,
    ) -> None:
        self.app = app
        self.scheduler = scheduler
        self.scheduler_folders = tuple(str(folder) for folder in scheduler_folders)
        self.process_provider = process_provider or WindowsProcessProvider()
        self.window_controller = window_controller or WindowsWindowController()
        self.process_controller = process_controller or WindowsProcessController()
        self.snapshot = RuntimeSnapshot()

    def refresh(self) -> RuntimeSnapshot:
        attached: list[RuntimeTarget] = []
        scheduler_targets: list[RuntimeTarget] = []
        diagnostics: list[str] = []

        if self.app is not None:
            project_path = _normalize_path(_optional_call(self.app, "GetProjectPath"))
            running = _optional_call(self.app, "HasRunningProcess")
            pid = _optional_call(self.app, "GetProcessId")
            handle = _optional_call(self.app, "GetWindowHandle")
            target_id = f"designer:{pid}" if pid is not None else "designer:attached"
            attached.append(
                RuntimeTarget(
                    target_id=target_id,
                    kind="designer",
                    pid=int(pid) if pid is not None else None,
                    project_path=project_path,
                    status="running" if running else "idle",
                    window_handle=int(handle) if handle is not None else None,
                    attached=True,
                )
            )

        if self.scheduler is not None:
            get_job = getattr(self.scheduler, "GetJobByFolder", None)
            if callable(get_job):
                for folder in self.scheduler_folders:
                    try:
                        job = get_job(folder)
                        if job is None:
                            continue
                        status = _optional_call(job, "Status", "unknown")
                        progress = _optional_call(job, "PercentComplete")
                        scheduler_targets.append(
                            RuntimeTarget(
                                target_id=f"scheduler:{folder}",
                                kind="scheduler",
                                status=str(status),
                                progress=(float(progress) if progress is not None else None),
                                metadata={"folder": folder},
                            )
                        )
                    except Exception as exc:
                        diagnostics.append(f"scheduler {folder}: {exc}")

        try:
            processes = list(self.process_provider.records())
        except Exception as exc:
            processes = []
            diagnostics.append(f"process discovery: {exc}")

        self.snapshot = RuntimeSnapshot(
            targets=tuple(merge_runtime_targets(attached, scheduler_targets, processes)),
            diagnostics=tuple(diagnostics),
        )
        return self.snapshot

    def watch(self, interval: float = 2.0, timeout: float | None = None) -> Iterator[RuntimeSnapshot]:
        if interval < 0:
            raise ValueError("interval must be non-negative")
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative")
        started = time.monotonic()
        while True:
            yield self.refresh()
            if timeout is not None and time.monotonic() - started >= timeout:
                return
            time.sleep(interval)

    def _target(self, target: str | RuntimeTarget) -> RuntimeTarget | None:
        target_id = target.target_id if isinstance(target, RuntimeTarget) else str(target)
        if self.snapshot.get(target_id) is None:
            self.refresh()
        return self.snapshot.get(target_id)

    def bring_to_front(self, target: str | RuntimeTarget) -> OperationResult:
        return self._window_operation(target, "bring_to_front", self.window_controller.bring_to_front)

    def minimize_to_background(self, target: str | RuntimeTarget) -> OperationResult:
        return self._window_operation(target, "minimize_to_background", self.window_controller.minimize)

    def _window_operation(self, target: str | RuntimeTarget, operation: str, action: Any) -> OperationResult:
        selected = self._target(target)
        target_id = target.target_id if isinstance(target, RuntimeTarget) else str(target)
        if selected is None:
            return _result(target_id, operation, False, "target was not found")
        if selected.window_handle is None:
            return _result(target_id, operation, False, "target has no controllable window handle")
        try:
            action(selected.window_handle)
        except Exception as exc:
            return _result(target_id, operation, False, "window operation failed", exc)
        return _result(target_id, operation, True, "window state changed")

    def stop_selected_jobs(self, targets: Iterable[str | RuntimeTarget], *, save: bool = False) -> list[OperationResult]:
        self.refresh()
        results: list[OperationResult] = []
        for requested in targets:
            selected = self._target(requested)
            target_id = requested.target_id if isinstance(requested, RuntimeTarget) else str(requested)
            if selected is None:
                results.append(_result(target_id, "stop", False, "target was not found"))
                continue
            if selected.kind == "scheduler":
                results.append(self._cancel_scheduler(selected))
                continue
            if selected.kind == "designer":
                results.append(self._cancel_designer(selected, save=save))
                continue
            results.append(_result(target_id, "stop", False, "unattached process has no safe JMAG stop API"))
        return results

    def stop_all_jobs(self, *, save: bool = False) -> list[OperationResult]:
        snapshot = self.refresh()
        return self.stop_selected_jobs(
            [target for target in snapshot.targets if target.kind in {"designer", "scheduler"}],
            save=save,
        )

    def _cancel_scheduler(self, target: RuntimeTarget) -> OperationResult:
        folder = str(target.metadata.get("folder", ""))
        try:
            job = self.scheduler.GetJobByFolder(folder)
            if job is None:
                return _result(target.target_id, "stop", False, "scheduler job was not found")
            job.Cancel()
        except Exception as exc:
            return _result(target.target_id, "stop", False, "scheduler cancellation failed", exc)
        return _result(target.target_id, "stop", True, "scheduler job cancelled")

    def _cancel_designer(self, target: RuntimeTarget, *, save: bool) -> OperationResult:
        if not target.attached or self.app is None:
            return _result(target.target_id, "stop", False, "Designer target is not attached to an Application")
        if save:
            try:
                self.app.Save()
            except Exception as exc:
                return _result(target.target_id, "stop", False, "project save failed; Designer was not stopped", exc)
        try:
            if target.status == "running":
                self.app.CancelProcess()
        except Exception as exc:
            return _result(target.target_id, "stop", False, "Designer cancellation failed", exc)
        message = "Designer calculation cancelled" if target.status == "running" else "Designer was already idle"
        return _result(target.target_id, "stop", True, message)

    def close_selected_designers(self, targets: Iterable[str | RuntimeTarget], *, save: bool = False) -> list[OperationResult]:
        self.refresh()
        results: list[OperationResult] = []
        for requested in targets:
            selected = self._target(requested)
            target_id = requested.target_id if isinstance(requested, RuntimeTarget) else str(requested)
            if selected is None or selected.kind != "designer":
                results.append(_result(target_id, "close", False, "target is not an attached Designer"))
                continue
            if not selected.attached or self.app is None:
                results.append(_result(target_id, "close", False, "Designer target is not attached to an Application"))
                continue
            try:
                if save:
                    self.app.Save()
                if selected.status == "running":
                    self.app.CancelProcess()
                self.app.Quit()
            except Exception as exc:
                results.append(_result(target_id, "close", False, "Designer close failed", exc))
                continue
            results.append(_result(target_id, "close", True, "Designer closed"))
        return results

    def save_and_close_all_designers(self) -> list[OperationResult]:
        snapshot = self.refresh()
        return self.close_selected_designers(
            [target for target in snapshot.targets if target.kind == "designer"],
            save=True,
        )

    def close_all_designers(self, *, save: bool = False) -> list[OperationResult]:
        snapshot = self.refresh()
        return self.close_selected_designers(
            [target for target in snapshot.targets if target.kind == "designer"],
            save=save,
        )

    def terminate_selected_processes(
        self,
        targets: Iterable[str | RuntimeTarget],
        *,
        force: bool = False,
    ) -> list[OperationResult]:
        self.refresh()
        results: list[OperationResult] = []
        for requested in targets:
            selected = self._target(requested)
            target_id = requested.target_id if isinstance(requested, RuntimeTarget) else str(requested)
            if not force:
                results.append(_result(target_id, "terminate", False, "force=True is required for process termination"))
                continue
            if selected is None or selected.pid is None:
                results.append(_result(target_id, "terminate", False, "target has no process ID"))
                continue
            try:
                self.process_controller.terminate(selected.pid)
            except Exception as exc:
                results.append(_result(target_id, "terminate", False, "process termination failed", exc))
                continue
            results.append(_result(target_id, "terminate", True, "process terminated"))
        return results


def list_running_jmag(**manager_options: Any) -> RuntimeSnapshot:
    return JMAGRuntimeManager(**manager_options).refresh()


def stop_all_jmag_jobs(*, save: bool = False, **manager_options: Any) -> list[OperationResult]:
    return JMAGRuntimeManager(**manager_options).stop_all_jobs(save=save)


def save_and_close_all_jmag(**manager_options: Any) -> list[OperationResult]:
    return JMAGRuntimeManager(**manager_options).save_and_close_all_designers()


def close_all_jmag_designers(*, save: bool = False, **manager_options: Any) -> list[OperationResult]:
    return JMAGRuntimeManager(**manager_options).close_all_designers(save=save)


__all__ = [
    "JMAGRuntimeManager",
    "OperationResult",
    "ProcessRecord",
    "RuntimeSnapshot",
    "RuntimeTarget",
    "close_all_jmag_designers",
    "list_running_jmag",
    "merge_runtime_targets",
    "parse_jproj_path",
    "process_records_from_rows",
    "save_and_close_all_jmag",
    "stop_all_jmag_jobs",
]
