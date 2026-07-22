"""Offline-safe orchestration for parametric JMAG Geometry Library templates."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol


_TEMPLATE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


class RegistrationStateError(RuntimeError):
    """Raised when a lifecycle operation is attempted out of order."""


@dataclass(frozen=True)
class GeometryTemplateSpec:
    """A self-contained parameter contract for one circular sector template."""

    template_id: str
    radius_mm: float = 100.0
    initial_angle_deg: float = 90.0
    insertion_angle_deg: float = 30.0
    library_folder: str = r"Custom Geometry\Codex"

    def __post_init__(self) -> None:
        if not _TEMPLATE_ID.fullmatch(self.template_id):
            raise ValueError("template_id must start with a letter and use only letters, digits, '_' or '-'")
        if not self.library_folder.startswith("Custom Geometry\\"):
            raise ValueError("library_folder must stay under 'Custom Geometry'")
        if self.radius_mm <= 0:
            raise ValueError("radius_mm must be greater than zero")
        if not 0 < self.initial_angle_deg < 360:
            raise ValueError("initial_angle_deg must be between 0 and 360")
        if not 0 < self.insertion_angle_deg < 360:
            raise ValueError("insertion_angle_deg must be between 0 and 360")

    @property
    def library_key(self) -> str:
        return f"{self.library_folder}\\{self.template_id}"

    @property
    def equation_names(self) -> dict[str, str]:
        return {"angle": "Angle", "radius": "Radius"}


class GeometryAdapter(Protocol):
    """Minimal JMAG-facing port; fake adapters keep workflow tests offline."""

    def build_sector(self, *, angle_deg: float, radius_mm: float, equation_names: Mapping[str, str]) -> None: ...
    def save_as(self, path: Path) -> None: ...
    def insert_library(self, library_key: str, rename_map: Mapping[str, str]) -> None: ...
    def set_equations(self, values: Mapping[str, float]) -> None: ...
    def read_equations(self, names: Mapping[str, str]) -> Mapping[str, float]: ...


@dataclass(frozen=True)
class TemplateRun:
    run_dir: Path
    jmdl_path: Path
    manifest_path: Path


class GeometryTemplateWorkflow:
    """Creates a safe run record and enforces build-register-insert ordering."""

    def __init__(self, spec: GeometryTemplateSpec, run_root: Path, *, run_id: str) -> None:
        if not run_id or any(char in run_id for char in r'\\/:*?"<>|'):
            raise ValueError("run_id must be a non-empty safe path component")
        self.spec = spec
        self.run_root = Path(run_root).resolve()
        self.run = TemplateRun(
            run_dir=self.run_root / f"{spec.template_id}_{run_id}",
            jmdl_path=self.run_root / f"{spec.template_id}_{run_id}" / f"{spec.template_id}.jmdl",
            manifest_path=self.run_root / f"{spec.template_id}_{run_id}" / "run_manifest.json",
        )
        self._status = "new"

    def build(self, geometry: GeometryAdapter) -> TemplateRun:
        if self.run.run_dir.exists():
            raise FileExistsError(f"Refusing to reuse existing run directory: {self.run.run_dir}")
        self.run.run_dir.mkdir(parents=True, exist_ok=False)
        geometry.build_sector(
            angle_deg=self.spec.initial_angle_deg,
            radius_mm=self.spec.radius_mm,
            equation_names=self.spec.equation_names,
        )
        geometry.save_as(self.run.jmdl_path)
        if not self.run.jmdl_path.is_file():
            raise RuntimeError(f"Geometry adapter did not create expected JMDL: {self.run.jmdl_path}")
        self._status = "built"
        self._write_manifest()
        return self.run

    def mark_registration_observed(self, library_key: str) -> None:
        self._require("built")
        if library_key != self.spec.library_key:
            raise ValueError(f"Registration key must be exactly '{self.spec.library_key}'")
        self._status = "registration_observed"
        self._write_manifest()

    def insert_and_verify(
        self,
        geometry: GeometryAdapter,
        *,
        rename_map: Mapping[str, str] | None = None,
    ) -> None:
        self._require("registration_observed")
        resolved_rename_map = dict(rename_map or {})
        geometry.insert_library(self.spec.library_key, resolved_rename_map)
        expected = {
            self.spec.equation_names["angle"]: self.spec.insertion_angle_deg,
            self.spec.equation_names["radius"]: self.spec.radius_mm,
        }
        geometry.set_equations(expected)
        actual = dict(geometry.read_equations(self.spec.equation_names))
        if actual != expected:
            raise RuntimeError(f"Inserted template equations differ: expected {expected}, got {actual}")
        self._status = "verified"
        self._write_manifest(rename_map=resolved_rename_map)

    def _require(self, expected: str) -> None:
        if self._status != expected:
            raise RegistrationStateError(f"Expected workflow state '{expected}', got '{self._status}'")

    def _write_manifest(self, *, rename_map: Mapping[str, str] | None = None) -> None:
        payload: dict[str, Any] = {
            "schema_version": 1,
            "status": self._status,
            "evidence_status": "observed" if self._status != "new" else "none",
            "spec": asdict(self.spec),
            "library_key": self.spec.library_key,
            "jmdl_path": str(self.run.jmdl_path),
        }
        if rename_map is not None:
            payload["rename_map"] = dict(rename_map)
        self.run.manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
