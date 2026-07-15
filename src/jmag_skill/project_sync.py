"""Deploy a locked subset of stable functions into a project."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(project: Path) -> None:
    lock = project / "jmag-functions.lock.json"
    package = project / "jmag_functions"
    if not lock.exists() or not package.exists():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    snapshot = project / ".jmag" / "history" / stamp
    snapshot.mkdir(parents=True)
    shutil.copy2(lock, snapshot / lock.name)
    shutil.copytree(package, snapshot / "jmag_functions")


def _safe_module(root: Path, module: str) -> Path:
    candidate = Path(module)
    if candidate.name != module or candidate.suffix != ".py" or not candidate.stem.isidentifier():
        raise ValueError(f"Unsafe catalog module path: {module!r}")
    resolved = (root / candidate).resolve()
    if root.resolve() not in resolved.parents or not resolved.is_file():
        raise ValueError(f"Catalog module is missing or outside the library: {module!r}")
    return resolved


def _package_init(entries: list[dict[str, Any]]) -> str:
    exports = sorted({(Path(entry["module"]).stem, entry["symbol"]) for entry in entries})
    lines = ['"""Project-locked JMAG functions."""', ""]
    lines.extend(f"from .{module} import {symbol}" for module, symbol in exports)
    lines.extend(["", "__all__ = ["])
    lines.extend(f'    "{symbol}",' for _, symbol in exports)
    lines.extend(["]", ""])
    return "\n".join(lines)


def _record_event(project: Path, action: str, lock: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc)
    folder = project / ".claude" / "memory" / now.strftime("%Y/%m/%d")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"jmag-{action}-{now.strftime('%H%M%S%f')}.md"
    ids = ", ".join(entry["id"] for entry in lock.get("functions", [])) or "none"
    target.write_text(
        f"# JMAG function {action}\n\n"
        f"- Library version: {lock.get('library_version', 'unknown')}\n"
        f"- Git commit: {lock.get('git_commit', 'unknown')}\n"
        f"- JMAG version: {lock.get('jmag_version', 'unknown')}\n"
        f"- Locked functions: {ids}\n",
        encoding="utf-8",
    )


def sync_project(
    project: Path | str, function_ids: Iterable[str], catalog: list[dict[str, Any]],
    library_root: Path | str, *, library_version: str, git_commit: str, jmag_version: str,
) -> dict[str, Any]:
    project_path, source_root = Path(project), Path(library_root)
    by_id = {entry["id"]: entry for entry in catalog if entry.get("status") == "stable"}
    requested = list(function_ids)
    selected: dict[str, dict[str, Any]] = {}

    def include(function_id: str) -> None:
        if function_id in selected:
            return
        if function_id not in by_id:
            raise KeyError(f"Stable function not found: {function_id}")
        entry = by_id[function_id]
        selected[function_id] = entry
        for dependency in entry.get("dependencies", []):
            include(dependency)

    for function_id in requested:
        include(function_id)
    selected_entries = list(selected.values())
    sources = {entry["module"]: _safe_module(source_root, entry["module"]) for entry in selected_entries}
    lock_path = project_path / "jmag-functions.lock.json"
    destination = project_path / "jmag_functions"
    (project_path / ".jmag" / "candidates").mkdir(parents=True, exist_ok=True)
    (project_path / ".claude" / "memory").mkdir(parents=True, exist_ok=True)
    if destination.exists() and not lock_path.exists() and any(destination.iterdir()):
        raise FileExistsError("Refusing to replace an unmanaged project jmag_functions directory")
    transaction = project_path / ".jmag" / "transactions" / uuid.uuid4().hex
    staged_package = transaction / "jmag_functions"
    staged_package.mkdir(parents=True)
    locked = []
    copied_modules: set[str] = set()
    for function_id, entry in selected.items():
        module = entry["module"]
        source = sources[module]
        if module not in copied_modules:
            shutil.copy2(source, staged_package / module)
            copied_modules.add(module)
        locked.append({"id": function_id, "module": module, "sha256": _sha256(source)})
    (staged_package / "__init__.py").write_text(_package_init(selected_entries), encoding="utf-8")
    lock = {
        "schema_version": 1, "library_version": library_version, "git_commit": git_commit,
        "jmag_version": jmag_version, "generated_at": datetime.now(timezone.utc).isoformat(),
        "functions": locked,
    }
    staged_lock = transaction / "jmag-functions.lock.json"
    staged_lock.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    _snapshot(project_path)
    old_package, old_lock = transaction / "old-jmag_functions", transaction / "old-lock.json"
    try:
        if destination.exists(): os.replace(destination, old_package)
        if lock_path.exists(): os.replace(lock_path, old_lock)
        os.replace(staged_package, destination)
        os.replace(staged_lock, lock_path)
    except Exception:
        if destination.exists() and destination != old_package:
            shutil.rmtree(destination)
        if old_package.exists(): os.replace(old_package, destination)
        if old_lock.exists(): os.replace(old_lock, lock_path)
        raise
    finally:
        if transaction.exists(): shutil.rmtree(transaction)
    readme = project_path / "README.md"
    if not readme.exists():
        readme.write_text(
            "# JMAG Project Adapter\n\n"
            "Purpose: run a reviewed subset of central JMAG functions.\n\n"
            "Inputs and outputs are defined by the locked function docstrings and project configuration; "
            "project paths, study names, response names, and limits remain local.\n\n"
            f"Supported JMAG version: {jmag_version}.\n\n"
            "Run the project entry point with JMAG 25.1 Python. Verify the central library with "
            "`jmag-skill verify`; inspect `jmag-functions.lock.json` before execution.\n",
            encoding="utf-8",
        )
    _record_event(project_path, "sync", lock)
    return lock


def rollback_project(project: Path | str) -> dict[str, Any]:
    project_path = Path(project)
    history = project_path / ".jmag" / "history"
    snapshots = sorted(path for path in history.iterdir() if path.is_dir()) if history.exists() else []
    if not snapshots:
        raise FileNotFoundError("No JMAG function snapshot is available")
    snapshot = snapshots[-1]
    current_lock_path = project_path / "jmag-functions.lock.json"
    previous_lock_path = snapshot / "jmag-functions.lock.json"
    previous = json.loads(previous_lock_path.read_text(encoding="utf-8"))
    current = json.loads(current_lock_path.read_text(encoding="utf-8")) if current_lock_path.exists() else {"functions": []}
    previous_modules = {entry["module"] for entry in previous["functions"]}
    for entry in current.get("functions", []):
        if entry["module"] not in previous_modules:
            stale = project_path / "jmag_functions" / entry["module"]
            if stale.is_file():
                stale.unlink()
    for source in (snapshot / "jmag_functions").iterdir():
        if source.is_file():
            shutil.copy2(source, project_path / "jmag_functions" / source.name)
    shutil.copy2(previous_lock_path, current_lock_path)
    shutil.rmtree(snapshot)
    _record_event(project_path, "rollback", previous)
    return previous
