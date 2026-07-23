from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from jmag_functions.project import (
    ManagedProjectSession,
    copy_project_bundle,
    load_protected_project_copy,
    open_protected_project_copy,
)


class FakeStudy:
    pass


class FakeModel:
    def __init__(self, study: FakeStudy | None = None) -> None:
        self.study = study or FakeStudy()

    def GetStudy(self, selector: str | int) -> FakeStudy | None:
        return self.study if selector != "missing" else None


class FakeApp:
    def __init__(self, study: FakeStudy | None = None, *, fail_load: bool = False) -> None:
        self.events: list[tuple[object, ...]] = []
        self.model = FakeModel(study)
        self.fail_load = fail_load
        self.quit_count = 0

    def Load(self, path: str) -> None:
        self.events.append(("load", path))
        if self.fail_load:
            raise RuntimeError("load failed")

    def GetCurrentModel(self) -> FakeModel:
        return self.model

    def SetStudyAsCurrent(self, study: FakeStudy) -> None:
        self.events.append(("select", study))

    def Save(self) -> None:
        self.events.append(("save",))

    def Quit(self) -> None:
        self.quit_count += 1


class ProtectedProjectCopyTests(unittest.TestCase):
    def make_source(self, root: Path, *, with_jfiles: bool = True) -> Path:
        source = root / "source.jproj"
        source.write_bytes(b"source project")
        if with_jfiles:
            files = source.with_suffix(".jfiles")
            (files / "nested").mkdir(parents=True)
            (files / "nested" / "result.jplot").write_bytes(b"result")
        return source

    def test_copy_is_filesystem_bundle_and_preserves_source_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            target = root / "run" / "copy.jproj"
            target.parent.mkdir()
            before = hashlib.sha256(source.read_bytes()).hexdigest()

            bundle = copy_project_bundle(source, target)

            self.assertEqual(bundle.project_path, target.resolve())
            self.assertEqual(bundle.result_directory, target.with_suffix(".jfiles").resolve())
            self.assertTrue(bundle.has_result_directory)
            self.assertEqual(target.read_bytes(), source.read_bytes())
            self.assertEqual(
                (target.with_suffix(".jfiles") / "nested" / "result.jplot").read_bytes(),
                b"result",
            )
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)

    def test_copy_without_jfiles_has_no_target_jfiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root, with_jfiles=False)
            target = root / "copy.jproj"

            bundle = copy_project_bundle(source, target)

            self.assertFalse(bundle.has_result_directory)
            self.assertFalse(target.with_suffix(".jfiles").exists())

    def test_copy_rejects_invalid_or_unsafe_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            target = root / "target.jproj"
            for bad_source in (root / "missing.jproj", root / "source.txt"):
                with self.assertRaises((FileNotFoundError, ValueError)):
                    copy_project_bundle(bad_source, target)
            with self.assertRaises(ValueError):
                copy_project_bundle(source, source)
            target.write_bytes(b"existing")
            with self.assertRaises(FileExistsError):
                copy_project_bundle(source, target)
            target.unlink()
            target.with_suffix(".jfiles").mkdir()
            with self.assertRaises(FileExistsError):
                copy_project_bundle(source, target)
            with self.assertRaises(FileNotFoundError):
                copy_project_bundle(source, root / "missing-parent" / "target.jproj")

    def test_copy_cleans_up_its_partial_target_after_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            target = root / "copy.jproj"
            with patch("jmag_functions.project.shutil.copytree", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    copy_project_bundle(source, target)
            self.assertFalse(target.exists())
            self.assertFalse(target.with_suffix(".jfiles").exists())

    def test_manifest_rejects_an_existing_path_and_tracks_transitions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            target = root / "copy.jproj"
            manifest = root / "manifest.json"
            manifest.write_text("already present", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                load_protected_project_copy(FakeApp(), source, target, manifest_path=manifest)
            manifest.unlink()

            session = load_protected_project_copy(FakeApp(), source, target, manifest_path=manifest)
            self.assertEqual(json.loads(manifest.read_text(encoding="utf-8"))["status"], "loaded")
            session.save()
            self.assertEqual(json.loads(manifest.read_text(encoding="utf-8"))["status"], "saved")
            session.close()
            record = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "closed")
            self.assertEqual(record["source_project_sha256_before"], record["source_project_sha256_after"])
            self.assertEqual(record["jmag_version"], "25.1")
            self.assertFalse(record["owns_application"])

    def test_owned_app_is_closed_after_load_failure_and_visible_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            target = root / "copy.jproj"
            failing = FakeApp(fail_load=True)
            creation_options: list[list[str]] = []
            designer = types.SimpleNamespace(
                CreateApplication=lambda options: creation_options.append(options) or failing
            )
            with patch.dict(sys.modules, {"jmag": types.ModuleType("jmag"), "jmag.designer": types.SimpleNamespace(designer=designer)}):
                with self.assertRaisesRegex(RuntimeError, "load failed"):
                    open_protected_project_copy(source, target, visible=True)
            self.assertEqual(creation_options, [[]])
            self.assertEqual(failing.quit_count, 1)

    def test_owned_and_borrowed_close_save_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            target = root / "owned.jproj"
            owned = FakeApp()
            designer = types.SimpleNamespace(CreateApplication=lambda options: owned)
            with patch.dict(sys.modules, {"jmag": types.ModuleType("jmag"), "jmag.designer": types.SimpleNamespace(designer=designer)}):
                session = open_protected_project_copy(source, target, visible=False, study="Main")
            self.assertIsInstance(session, ManagedProjectSession)
            self.assertTrue(session.owns_application)
            session.close(save=True)
            self.assertIn(("save",), owned.events)
            self.assertEqual(owned.quit_count, 1)
            session.close()
            self.assertEqual(owned.quit_count, 1)
            with self.assertRaisesRegex(RuntimeError, "closed"):
                session.save()
            with self.assertRaisesRegex(RuntimeError, "closed"):
                session.select_study("Main")

            borrowed_target = root / "borrowed.jproj"
            borrowed = FakeApp()
            borrowed_session = load_protected_project_copy(borrowed, source, borrowed_target)
            borrowed_session.close()
            self.assertNotIn(("save",), borrowed.events)
            self.assertEqual(borrowed.quit_count, 0)

    def test_missing_study_fails_closed_without_quitting_borrowed_app(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            borrowed = FakeApp()
            with self.assertRaisesRegex(RuntimeError, "study not found"):
                load_protected_project_copy(borrowed, source, root / "copy.jproj", study="missing")
            self.assertEqual(borrowed.quit_count, 0)


if __name__ == "__main__":
    unittest.main()
