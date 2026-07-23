"""Explicit, non-destructive M1 JMAG Designer 25.1 smoke test.

Run only after separately authorizing the source, fresh target, optional study,
Designer launch, and saving the target copy. The script never selects a source
automatically and never runs a Study, solver, Scheduler, or result deletion.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

from _jmag_user_env import configure_environment


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--study", default=None)
    parser.add_argument("--visible", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    source = args.source.resolve()
    target = args.target.resolve()
    manifest = args.manifest.resolve()
    if source.suffix.lower() != ".jproj" or target.suffix.lower() != ".jproj":
        print("source and target must be .jproj files", file=sys.stderr)
        return 2
    if source == target or not source.is_file() or target.exists() or target.with_suffix(".jfiles").exists():
        print("unsafe source or target; target bundle must be absent", file=sys.stderr)
        return 2
    if manifest.exists() or not target.parent.is_dir() or not manifest.parent.is_dir():
        print("manifest must be new and both target parents must exist", file=sys.stderr)
        return 2

    source_hash_before = _sha256(source)
    configure_environment()
    from jmag_functions import open_protected_project_copy

    try:
        with open_protected_project_copy(
            source,
            target,
            visible=args.visible,
            study=args.study,
            manifest_path=manifest,
        ) as session:
            session.save()
    except (FileNotFoundError, FileExistsError, ValueError) as error:
        print(f"input or target validation failed: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        print(f"JMAG load/select/save failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 3

    source_hash_after = _sha256(source)
    source_has_jfiles = source.with_suffix(".jfiles").is_dir()
    target_has_jfiles = target.with_suffix(".jfiles").is_dir()
    if (
        source_hash_before != source_hash_after
        or not target.is_file()
        or source_has_jfiles != target_has_jfiles
        or not manifest.is_file()
    ):
        print("post-run source or bundle verification failed", file=sys.stderr)
        return 1
    print(f"M1 smoke passed; manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
