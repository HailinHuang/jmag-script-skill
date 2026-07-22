"""Tkinter frontend for inspecting and safely controlling JMAG runtimes."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Callable, Iterable


_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ImportError as exc:  # pragma: no cover - depends on the host Python build.
    tk = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]
    _TKINTER_ERROR = exc
else:
    _TKINTER_ERROR = None

from jmag_functions.runtime import (
    JMAGRuntimeManager,
    OperationResult,
    RuntimeSnapshot,
    RuntimeTarget,
)


COLUMNS = (
    ("kind", "Kind", 90),
    ("id", "Target ID", 180),
    ("pid", "PID", 75),
    ("status", "Status", 100),
    ("progress", "Progress", 90),
    ("project", "Project", 300),
    ("window", "Window", 90),
    ("attached", "Attached", 85),
)


def _display(value: Any) -> str:
    return "" if value is None else str(value)


def format_runtime_target(target: RuntimeTarget) -> tuple[str, ...]:
    """Convert a runtime target into the stable table row representation."""
    progress = "" if target.progress is None else f"{target.progress:.1f}%"
    return (
        target.kind,
        target.target_id,
        _display(target.pid),
        target.status,
        progress,
        _display(target.project_path),
        _display(target.window_handle),
        "Yes" if target.attached else "No",
    )


def operation_result_messages(results: Iterable[OperationResult]) -> list[str]:
    """Render operation results for the frontend log."""
    messages: list[str] = []
    for result in results:
        prefix = "OK" if result.ok else "ERROR"
        detail = f" ({result.error})" if result.error else ""
        messages.append(f"[{prefix}] {result.target_id}: {result.message}{detail}")
    return messages


class RuntimeFrontendModel:
    """Small presentation boundary around the reusable runtime manager."""

    def __init__(self, manager: JMAGRuntimeManager) -> None:
        self.manager = manager

    def refresh(self) -> RuntimeSnapshot:
        return self.manager.refresh()


class RuntimeFrontendApp:
    """Tkinter application for one or more JMAG runtime targets."""

    def __init__(
        self,
        root: Any,
        *,
        manager: JMAGRuntimeManager | None = None,
        poll_ms: int = 2000,
        start_polling: bool = True,
    ) -> None:
        if poll_ms <= 0:
            raise ValueError("poll_ms must be positive")
        self.root = root
        self.manager = manager or JMAGRuntimeManager()
        self.model = RuntimeFrontendModel(self.manager)
        self.poll_ms = poll_ms
        self._timer: Any | None = None
        self._closed = False
        self.current_snapshot = RuntimeSnapshot()

        self._build_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        if start_polling:
            self.refresh()

    def _build_widgets(self) -> None:
        if ttk is None or tk is None:  # pragma: no cover - host-dependent.
            raise RuntimeError(f"Tkinter is unavailable: {_TKINTER_ERROR}")

        self.root.title("JMAG Runtime Frontend")
        self.root.geometry("1280x720")
        self.root.minsize(900, 520)

        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side="left")
        ttk.Label(toolbar, text="Polling: 2 seconds").pack(side="left", padx=10)
        self.status_var = tk.StringVar(self.root, value="Ready")
        ttk.Label(toolbar, textvariable=self.status_var).pack(side="right")

        table_frame = ttk.Frame(outer)
        table_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(
            table_frame,
            columns=[column[0] for column in COLUMNS],
            show="headings",
            selectmode="browse",
        )
        for key, heading, width in COLUMNS:
            self.tree.heading(key, text=heading)
            self.tree.column(key, width=width, anchor="w", stretch=key == "project")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        normal_actions = ttk.LabelFrame(outer, text="JMAG controls", padding=8)
        normal_actions.pack(fill="x", pady=(8, 0))
        buttons = (
            ("Bring to Front", self.bring_selected_to_front),
            ("Minimize", self.minimize_selected),
            ("Stop Job / Calculation", self.stop_selected),
            ("Save and Close Designer", self.save_close_selected),
            ("Close Designer", self.close_selected),
        )
        for label, command in buttons:
            ttk.Button(normal_actions, text=label, command=command).pack(side="left", padx=(0, 6))
        ttk.Button(
            normal_actions,
            text="Force Terminate Process",
            command=self.force_terminate_selected,
        ).pack(side="right")

        log_frame = ttk.LabelFrame(outer, text="Activity log", padding=6)
        log_frame.pack(fill="x", pady=(8, 0))
        self.log = tk.Text(log_frame, height=6, state="disabled", wrap="word")
        self.log.pack(fill="x", expand=True)

    def _selected_target_id(self) -> str | None:
        selected = self.tree.selection()
        return str(selected[0]) if selected else None

    def _append_log(self, lines: Iterable[str]) -> None:
        messages = list(lines)
        if not messages:
            return
        self.log.configure(state="normal")
        for message in messages:
            self.log.insert("end", f"{message}\n")
        self.log.configure(state="disabled")
        self.log.see("end")

    def refresh(self, *, schedule: bool = True) -> RuntimeSnapshot:
        previous = self._selected_target_id()
        try:
            snapshot = self.model.refresh()
        except Exception as exc:
            self._append_log([f"[ERROR] refresh: {type(exc).__name__}: {exc}"])
            if hasattr(self, "status_var"):
                self.status_var.set("Refresh failed")
            return self.current_snapshot

        self.current_snapshot = snapshot
        for item in self.tree.get_children():
            self.tree.delete(item)
        for target in snapshot.targets:
            self.tree.insert("", "end", iid=target.target_id, values=format_runtime_target(target))
        if previous and snapshot.get(previous) is not None:
            self.tree.selection_set(previous)
        if snapshot.diagnostics:
            self._append_log(f"[DIAGNOSTIC] {message}" for message in snapshot.diagnostics)
        if hasattr(self, "status_var"):
            self.status_var.set(f"{len(snapshot.targets)} target(s) found")
        if schedule and not self._closed:
            self._timer = self.root.after(self.poll_ms, self.refresh)
        return snapshot

    def _run_operation(self, action: Callable[[str], Iterable[OperationResult] | OperationResult]) -> list[OperationResult]:
        target_id = self._selected_target_id()
        if target_id is None:
            self._append_log(["[ERROR] No target selected"])
            return []
        try:
            result = action(target_id)
            results = [result] if isinstance(result, OperationResult) else list(result)
        except Exception as exc:
            self._append_log([f"[ERROR] {target_id}: {type(exc).__name__}: {exc}"])
            return []
        self._append_log(operation_result_messages(results))
        self.refresh(schedule=False)
        return results

    def bring_selected_to_front(self) -> list[OperationResult]:
        return self._run_operation(self.manager.bring_to_front)

    def minimize_selected(self) -> list[OperationResult]:
        return self._run_operation(self.manager.minimize_to_background)

    def stop_selected(self) -> list[OperationResult]:
        return self._run_operation(lambda target_id: self.manager.stop_selected_jobs([target_id]))

    def save_close_selected(self) -> list[OperationResult]:
        return self._run_operation(
            lambda target_id: self.manager.close_selected_designers([target_id], save=True)
        )

    def close_selected(self) -> list[OperationResult]:
        return self._run_operation(
            lambda target_id: self.manager.close_selected_designers([target_id], save=False)
        )

    def confirm_force_termination(self, target: RuntimeTarget) -> bool:
        if messagebox is None:  # pragma: no cover - host-dependent.
            return False
        process_name = target.metadata.get("process_name", "unknown process")
        return bool(
            messagebox.askyesno(
                "Confirm force termination",
                f"Terminate {process_name} (PID {target.pid})?\n\n"
                "This is a last-resort operation and may lose unsaved work.",
                parent=self.root,
            )
        )

    def force_terminate_selected(self) -> list[OperationResult]:
        target_id = self._selected_target_id()
        if target_id is None:
            self._append_log(["[ERROR] No target selected"])
            return []
        target = self.current_snapshot.get(target_id)
        if target is None:
            self._append_log([f"[ERROR] {target_id}: target is not in the current snapshot"])
            return []
        if not self.confirm_force_termination(target):
            self._append_log([f"[INFO] {target_id}: force termination cancelled"])
            return []
        return self._run_operation(
            lambda selected_id: self.manager.terminate_selected_processes(
                [selected_id], force=True
            )
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._timer is not None:
            self.root.after_cancel(self._timer)
            self._timer = None
        self.root.destroy()


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JMAG Runtime Frontend")
    parser.add_argument(
        "--poll-ms",
        type=_positive_integer,
        default=2000,
        help="refresh interval in milliseconds (default: 2000)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if tk is None:
        print(f"Tkinter is unavailable: {_TKINTER_ERROR}", file=sys.stderr)
        return 1
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"Unable to start the Tkinter frontend: {exc}", file=sys.stderr)
        return 1
    RuntimeFrontendApp(root, poll_ms=args.poll_ms)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
