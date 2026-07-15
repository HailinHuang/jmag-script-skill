"""Command-line entry point for retrieval, inspection, promotion, sync and verification."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .help_index import build_help_index
from .retrieval import HelpIndex, search_catalog, search_knowledge


ROOT = Path(__file__).resolve().parents[2]
REFERENCES = ROOT / "references"
DEFAULT_HELP = Path(r"C:\Program Files\JMAG-Designer25.1\Help\en\Script")
__version__ = "0.1.0"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _print(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jmag-skill")
    sub = parser.add_subparsers(dest="command", required=True)
    search = sub.add_parser("search"); search.add_argument("requirement"); search.add_argument("--limit", type=int, default=5)
    help_cmd = sub.add_parser("help"); help_cmd.add_argument("query"); help_cmd.add_argument("--max-topics", type=int, default=3); help_cmd.add_argument("--help-root", type=Path, default=DEFAULT_HELP)
    inspect = sub.add_parser("inspect"); inspect.add_argument("file", type=Path); inspect.add_argument("--function", required=True); inspect.add_argument("--output", type=Path)
    promotion = sub.add_parser("promote"); promotion.add_argument("candidate", type=Path); promotion.add_argument("--approved", action="store_true"); promotion.add_argument("--output", type=Path)
    sync = sub.add_parser("sync"); sync.add_argument("project", type=Path); sync.add_argument("--functions", nargs="+", required=True); sync.add_argument("--jmag-version", default="25.1")
    rollback = sub.add_parser("rollback"); rollback.add_argument("project", type=Path)
    sub.add_parser("verify")
    index = sub.add_parser("build-index"); index.add_argument("--help-root", type=Path, default=DEFAULT_HELP)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "search":
        _print({
            "functions": search_catalog(_json(REFERENCES / "function-catalog.json")["functions"], args.requirement, args.limit),
            "know_how": search_knowledge(_json(REFERENCES / "knowledge-catalog.json")["entries"], args.requirement, 3),
        }); return 0
    if args.command == "help":
        index = HelpIndex(REFERENCES / "help-index.jsonl", args.help_root)
        _print(index.extract(index.search(args.query, args.max_topics), args.max_topics)); return 0
    if args.command == "inspect":
        from .candidate import inspect_function
        result = inspect_function(args.file, args.function)
        if args.output: args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        _print(result); return 0
    if args.command == "promote":
        from .promotion import promote
        result = promote(_json(args.candidate), approved=args.approved)
        target = args.output or args.candidate
        target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        _print(result); return 0
    if args.command == "sync":
        from .project_sync import sync_project
        catalog = _json(REFERENCES / "function-catalog.json")["functions"]
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or "uncommitted"
        result = sync_project(args.project, args.functions, catalog, ROOT / "src" / "jmag_functions", library_version=__version__, git_commit=commit, jmag_version=args.jmag_version)
        _print(result); return 0
    if args.command == "rollback":
        from .project_sync import rollback_project
        _print(rollback_project(args.project)); return 0
    if args.command == "build-index":
        _print({"entries": build_help_index(args.help_root, REFERENCES / "help-index.jsonl")}); return 0
    if args.command == "verify":
        completed = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"], cwd=ROOT)
        return completed.returncode
    return 2


if __name__ == "__main__": raise SystemExit(main())
