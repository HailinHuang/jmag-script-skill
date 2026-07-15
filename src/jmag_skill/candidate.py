"""Static candidate manifest generation; this module never promotes code."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from typing import Any


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


def inspect_function(path: Path | str, function_name: str) -> dict[str, Any]:
    source_path = Path(path)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    function = next((node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name), None)
    if function is None:
        raise KeyError(f"Function not found: {function_name}")
    module_globals = [
        target.id for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in ((node.targets if isinstance(node, ast.Assign) else [node.target]))
        if isinstance(target, ast.Name)
    ]
    strings = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    paths = [value for value in strings if re.search(r"(?:^[A-Za-z]:[/\\]|[/\\].+[/\\])", value)]
    calls = [name for node in ast.walk(function) if isinstance(node, ast.Call) and (name := _call_name(node))]
    jmag_methods = sorted({name for name in calls if name[:1].isupper()})
    signature = f"{function.name}({ast.unparse(function.args)})"
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    return {
        "id": f"observed.{function_name}", "state": "observed", "function": function_name,
        "signature": signature, "source": str(source_path), "source_sha256": digest,
        "dependencies": sorted(set(calls) - set(jmag_methods)),
        "jmag_methods": jmag_methods, "help_sources": [],
        "global_dependencies": sorted(module_globals), "hardcoded_paths": sorted(set(paths)),
        "project_constants": [], "test_evidence": [], "run_evidence": [],
        "jmag_versions": [], "similarity": [],
    }
