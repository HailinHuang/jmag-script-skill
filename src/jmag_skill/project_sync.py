"""Deploy a locked subset of stable functions into a project."""

from __future__ import annotations

import hashlib
import json
import shutil
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
    _snapshot(project_path)
    destination = project_path / "jmag_functions"
    destination.mkdir(parents=True, exist_ok=True)
    (project_path / ".jmag" / "candidates").mkdir(parents=True, exist_ok=True)
    (project_path / ".claude" / "memory").mkdir(parents=True, exist_ok=True)
    init = destination / "__init__.py"
    if not init.exists():
        init.write_text('"""Project-locked JMAG functions."""\n', encoding="utf-8")
    locked = []
    copied_modules: set[str] = set()
    for function_id, entry in selected.items():
        module = entry["module"]
        source = source_root / module
        if module not in copied_modules:
            shutil.copy2(source, destination / module)
            copied_modules.add(module)
        locked.append({"id": function_id, "module": module, "sha256": _sha256(source)})
    lock = {
        "schema_version": 1, "library_version": library_version, "git_commit": git_commit,
        "jmag_version": jmag_version, "generated_at": datetime.now(timezone.utc).isoformat(),
        "functions": locked,
    }
    (project_path / "jmag-functions.lock.json").write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    readme = project_path / "README.md"
    if not readme.exists():
        readme.write_text(
            "# JMAG Project Adapter\n\nFunctions are pinned by `jmag-functions.lock.json`.\n"
            f"Supported JMAG version: {jmag_version}.\n\nVerify with `jmag-skill verify`.\n",
            encoding="utf-8",
        )
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
    return previous
