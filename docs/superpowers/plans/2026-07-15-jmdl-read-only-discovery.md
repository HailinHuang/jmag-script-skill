# Read-Only JMDL Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable offline `jmag-skill inspect-jmdl` command that inventories a JMDL archive, builds parameter and reference graphs, reports evidence-backed semantic hypotheses, and generates deterministic JSON and Markdown outputs without modifying the source or requiring JMAG.

**Architecture:** A narrow archive adapter owns undocumented ZIP/XML/DAT details and maps them into a stable domain model. Separate graph, analysis, and rendering modules operate only on that model; the CLI is a thin orchestration boundary with explicit, atomic outputs. Future live-JMAG and mutation components are documented but not implemented.

**Tech Stack:** Python 3.10+ standard library (`argparse`, `dataclasses`, `hashlib`, `json`, `pathlib`, `re`, `tempfile`, `xml.etree.ElementTree`, `zipfile`), `unittest`, JSON Schema document without a runtime validation dependency.

## Global Constraints

- The source JMDL is always read-only; never load or save it through JMAG, extract over it, mutate XML/DAT, run a study, delete results, or rebuild geometry.
- Keep all new runtime code under `src/jmag_skill`; do not modify `src/jmag_functions`, stable catalogs, promotion state, or project-sync behavior.
- Use no third-party runtime dependency and require no JMAG installation for the offline test suite.
- Keep undocumented XML and DAT knowledge inside `jmdl_archive.py`; downstream modules consume domain records only.
- Retrieve no additional JMAG Help unless a later task cannot be completed from the three already anchored topics; any iteration remains capped at three closely related topics.
- Preserve uncertain classifications as hypotheses with evidence, confidence, and confirmation status; never identify `Sketch.2` as a winding with certainty.
- Keep the binary `Test_JMAG_Model_Files.jmdl` local and untracked unless the user explicitly authorizes committing it.
- Use deterministic ordering and exclude timestamps, absolute paths, and machine-specific data from golden snapshots.
- Run the full offline suite before every commit. If the sandbox blocks `tempfile`, rerun the identical command with approved temporary-directory access.

---

## File Structure

- Create `src/jmag_skill/jmdl_model.py`: domain records, enums, inventory serialization, discovery exceptions.
- Create `src/jmag_skill/jmdl_archive.py`: read-only ZIP integrity, version/XML parsing, raw native-object and DAT-reference extraction.
- Create `src/jmag_skill/jmdl_graph.py`: expression tokenization, dependency edges, cycle and undefined-variable detection.
- Create `src/jmag_skill/jmdl_analysis.py`: native reference resolution, diagnostics, parameter consumers, and semantic hypotheses.
- Create `src/jmag_skill/jmdl_render.py`: deterministic inventory JSON and Markdown report rendering.
- Create `src/jmag_skill/jmdl_discovery.py`: orchestration and atomic output writing.
- Modify `src/jmag_skill/cli.py`: register `inspect-jmdl` and map discovery errors to exit codes.
- Create `schemas/jmdl-inventory.schema.json`: documented output contract.
- Create `tests/fixtures/jmdl_minimal.xml`: synthetic XML containing representative parameter, sketch, pattern, reference, and diagnostic cases.
- Create `tests/fixtures/sample_inventory.golden.json`: normalized golden snapshot based on the supplied model.
- Create `tests/fixtures/sample_report.golden.md`: deterministic report snapshot.
- Create `tests/unit/test_jmdl_model.py`, `test_jmdl_archive.py`, `test_jmdl_graph.py`, `test_jmdl_analysis.py`, and `test_jmdl_render.py`.
- Create `tests/integration/test_jmdl_cli.py` and `test_jmdl_sample.py`.
- Create the six requested documents/artifacts: `docs/jmdl_format_observations.md`, `artifacts/sample_inventory.json`, `artifacts/sample_report.md`, `docs/architecture.md`, `docs/jmag_api_evidence.md`, and `docs/implementation_plan.md`.

---

### Task 1: Domain Model and Inventory Schema

**Files:**
- Create: `src/jmag_skill/jmdl_model.py`
- Create: `schemas/jmdl-inventory.schema.json`
- Test: `tests/unit/test_jmdl_model.py`

**Interfaces:**
- Consumes: no new project interface.
- Produces: `Evidence`, `NativeObject`, `Parameter`, `GraphEdge`, `Diagnostic`, `SemanticHypothesis`, `Inventory`, `DiscoveryError`, `UsageDiscoveryError`, `ArchiveDiscoveryError`, and `UnsupportedStructureError`; `Inventory.to_dict() -> dict[str, object]`.

- [ ] **Step 1: Write the failing domain-model tests**

```python
import unittest

from jmag_skill.jmdl_model import (
    Diagnostic, Evidence, Inventory, NativeObject, Parameter,
    SemanticHypothesis,
)


class JmdlModelTests(unittest.TestCase):
    def test_inventory_serialization_is_stable_and_separates_hypotheses(self):
        inventory = Inventory(
            schema_version="1.0",
            source={"filename": "sample.jmdl", "sha256": "abc", "zip_integrity": "ok"},
            native_objects=(
                NativeObject("2", "TSketch", "Sketch.2", None, True, False, True, Evidence("modeller_project.xml", "key:2")),
                NativeObject("1", "TSketch", "rotor", None, True, False, True, Evidence("modeller_project.xml", "key:1")),
            ),
            parameters=(Parameter("Rro", "Rsi-airgap", 79.5, ("Rsi", "airgap")),),
            diagnostics=(Diagnostic("warning", "duplicate-name", "duplicate", ("1", "2")),),
            semantic_hypotheses=(
                SemanticHypothesis("2", "winding-related-geometry", "low", ("rule:pattern-shape",), False),
            ),
        )
        payload = inventory.to_dict()
        self.assertEqual([item["id"] for item in payload["native_objects"]], ["1", "2"])
        self.assertNotIn("semantic_type", payload["native_objects"][1])
        self.assertEqual(payload["semantic_hypotheses"][0]["confidence"], "low")

    def test_inventory_rejects_absolute_source_paths(self):
        with self.assertRaises(ValueError):
            Inventory.empty({"filename": r"C:\\private\\sample.jmdl"})
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.unit.test_jmdl_model -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'jmag_skill.jmdl_model'`.

- [ ] **Step 3: Implement the minimal typed domain model**

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import PurePath
from typing import Any


class DiscoveryError(Exception):
    exit_code = 4


class UsageDiscoveryError(DiscoveryError):
    exit_code = 2


class ArchiveDiscoveryError(DiscoveryError):
    exit_code = 3


class UnsupportedStructureError(DiscoveryError):
    exit_code = 4


@dataclass(frozen=True)
class Evidence:
    member: str
    locator: str


@dataclass(frozen=True)
class NativeObject:
    id: str
    type: str
    name: str | None
    parent_id: str | None
    valid: bool | None
    suppressed: bool | None
    visible: bool | None
    evidence: Evidence
    properties: dict[str, Any] = field(default_factory=dict)
    references: tuple[str, ...] = ()


@dataclass(frozen=True)
class Parameter:
    name: str
    expression: str
    value: float | int | str | None
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    kind: str


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    object_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class SemanticHypothesis:
    object_id: str
    semantic_type: str
    confidence: str
    evidence: tuple[str, ...]
    user_confirmed: bool


@dataclass(frozen=True)
class Inventory:
    schema_version: str
    source: dict[str, Any]
    native_objects: tuple[NativeObject, ...] = ()
    parameters: tuple[Parameter, ...] = ()
    dependency_graph: tuple[GraphEdge, ...] = ()
    relationships: tuple[GraphEdge, ...] = ()
    geometry: dict[str, Any] = field(default_factory=dict)
    diagnostics: tuple[Diagnostic, ...] = ()
    semantic_hypotheses: tuple[SemanticHypothesis, ...] = ()

    def __post_init__(self) -> None:
        filename = str(self.source.get("filename", ""))
        if PurePath(filename).name != filename:
            raise ValueError("source filename must not contain a path")

    @classmethod
    def empty(cls, source: dict[str, Any]) -> "Inventory":
        return cls(schema_version="1.0", source=source)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("native_objects", "parameters", "dependency_graph", "relationships", "diagnostics", "semantic_hypotheses"):
            payload[key] = sorted(payload[key], key=lambda item: tuple(str(value) for value in item.values()))
        return payload
```

Define `schemas/jmdl-inventory.schema.json` with required top-level fields `schema_version`, `source`, `native_objects`, `parameters`, `dependency_graph`, `relationships`, `geometry`, `diagnostics`, and `semantic_hypotheses`; set `additionalProperties` to `false` at the top level and require confidence to be one of `low`, `medium`, or `high`.

- [ ] **Step 4: Run the focused and full tests**

Run: `python -m unittest tests.unit.test_jmdl_model -v`

Expected: 2 tests PASS.

Run: `python -m unittest discover -s tests -v`

Expected: all existing and new offline tests PASS; the real-JMAG smoke remains skipped unless explicitly enabled.

- [ ] **Step 5: Commit the domain contract**

```text
git add src/jmag_skill/jmdl_model.py schemas/jmdl-inventory.schema.json tests/unit/test_jmdl_model.py
git commit -m "feat: define JMDL inventory model"
```

---

### Task 2: Read-Only Archive Adapter

**Files:**
- Create: `src/jmag_skill/jmdl_archive.py`
- Create: `tests/fixtures/jmdl_minimal.xml`
- Test: `tests/unit/test_jmdl_archive.py`

**Interfaces:**
- Consumes: `Evidence`, `NativeObject`, `Parameter`, `ArchiveDiscoveryError`, and `UnsupportedStructureError` from Task 1.
- Produces: `ArchiveSnapshot`; `read_jmdl(path: Path) -> ArchiveSnapshot`; `ArchiveSnapshot.source_metadata() -> dict[str, object]`.

- [ ] **Step 1: Write failing ZIP, XML, version, and read-only tests**

```python
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path

from jmag_skill.jmdl_archive import read_jmdl
from jmag_skill.jmdl_model import ArchiveDiscoveryError


class JmdlArchiveTests(unittest.TestCase):
    def _archive(self, root: Path, xml: str) -> Path:
        path = root / "sample.jmdl"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("info.txt", "Version: 251\nSaveVersion: 251\nCreationVersion: 251\n")
            archive.writestr("modeller_project.xml", xml)
            archive.writestr("modeller_data00000002.dat", b"TSketchArc1\x00")
        return path

    def test_reads_versions_parameters_objects_and_dat_references_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._archive(Path(tmp), Path("tests/fixtures/jmdl_minimal.xml").read_text(encoding="utf-8"))
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            snapshot = read_jmdl(source)
            after = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(before, after)
            self.assertEqual(snapshot.saved_version, 251)
            self.assertEqual(len(snapshot.parameters), 4)
            self.assertIn("modeller_data00000002.dat", snapshot.dat_members)
            self.assertEqual({obj.name for obj in snapshot.objects if obj.type == "TSketch"}, {"Stator_yoke", "Sketch.2"})

    def test_bad_zip_is_exit_three_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "bad.jmdl"
            source.write_bytes(b"not-a-zip")
            with self.assertRaises(ArchiveDiscoveryError):
                read_jmdl(source)
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.unit.test_jmdl_archive -v`

Expected: FAIL because `jmdl_archive` does not exist.

- [ ] **Step 3: Add the synthetic XML fixture**

Create a compact `modeller` document containing:

```xml
<modeller original_version="210" saved_version="251">
  <TParametricDesignTable items_size="4">
    <TParametricEquation name="Slot_Number" expr="54" value="54" />
    <TParametricEquation name="Rso" expr="116.5" value="116.5" />
    <TParametricEquation name="Rsi" expr="Rso-19-16-1-1.2" value="79.3" />
    <TParametricEquation name="Rro" expr="Rsi-0.8" value="78.5" />
  </TParametricDesignTable>
  <TSketch key="10" name="Stator_yoke" is_valid="1" suppress="0" visible="1">
    <TRegionRadialPattern key="20" name="Region Circular Pattern.3" angle_expr="360/Slot_Number" instance_expr="Slot_Number/6" target_ref="30" />
  </TSketch>
  <TSketch key="11" name="Sketch.2" is_valid="1" suppress="0" visible="1" cached_ref="modeller_data00000002.dat-1" />
  <TRegion key="30" name="Region.1" />
</modeller>
```

- [ ] **Step 4: Implement the archive adapter with no extraction**

```python
@dataclass(frozen=True)
class ArchiveSnapshot:
    filename: str
    size: int
    sha256: str
    versions: dict[str, int]
    original_version: int | None
    saved_version: int
    members: tuple[str, ...]
    dat_members: tuple[str, ...]
    objects: tuple[NativeObject, ...]
    parameters: tuple[Parameter, ...]
    raw_references: tuple[tuple[str, str, str], ...]

    def source_metadata(self) -> dict[str, object]:
        return {
            "filename": self.filename,
            "size": self.size,
            "sha256": self.sha256,
            "zip_integrity": "ok",
            "versions": dict(sorted(self.versions.items())),
            "members": list(self.members),
        }


def read_jmdl(path: Path) -> ArchiveSnapshot:
    source = path.resolve(strict=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    try:
        with zipfile.ZipFile(source, "r") as archive:
            corrupt = archive.testzip()
            if corrupt:
                raise ArchiveDiscoveryError(f"CRC failure in {corrupt}")
            names = tuple(sorted(archive.namelist()))
            if names.count("modeller_project.xml") != 1:
                raise UnsupportedStructureError("expected exactly one modeller_project.xml")
            info = archive.read("info.txt").decode("utf-8", errors="replace") if "info.txt" in names else ""
            root = ET.fromstring(archive.read("modeller_project.xml"))
    except (zipfile.BadZipFile, ET.ParseError, OSError) as exc:
        raise ArchiveDiscoveryError(str(exc)) from exc
    versions = _parse_versions(info)
    objects = _parse_native_objects(root)
    parameters = _parse_parameters(root)
    dat_members = tuple(name for name in names if name.startswith("modeller_data") and name.endswith(".dat"))
    return ArchiveSnapshot(
        filename=source.name,
        size=source.stat().st_size,
        sha256=digest,
        versions=versions,
        original_version=_optional_int(root.attrib.get("original_version")),
        saved_version=_required_int(root.attrib.get("saved_version"), "saved_version"),
        members=names,
        dat_members=dat_members,
        objects=objects,
        parameters=parameters,
        raw_references=_parse_references(root),
    )
```

Implement the helpers with these exact entry points. Keep all element-name and attribute fallbacks in this module:

```python
def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_versions(info: str) -> dict[str, int]:
    versions = {}
    for key in ("Version", "SaveVersion", "CreationVersion"):
        match = re.search(rf"(?m)^{key}:\s*(\d+)\s*$", info)
        if match:
            versions[key] = int(match.group(1))
    return versions


def _parse_parameters(root: ET.Element) -> tuple[Parameter, ...]:
    records = []
    for element in root.iter():
        if _local_name(element.tag) != "TParametricEquation":
            continue
        name = _attribute_or_child_text(element, ("name",))
        expression = _attribute_or_child_text(element, ("expr", "expression")) or ""
        value = _parse_saved_value(_attribute_or_child_text(element, ("value",)))
        if name:
            records.append(Parameter(name, expression, value, ()))
    return tuple(sorted(records, key=lambda item: item.name))


def _parse_native_objects(root: ET.Element) -> tuple[NativeObject, ...]:
    records = []
    for element in root.iter():
        key = element.attrib.get("key")
        type_name = element.attrib.get("type") or _local_name(element.tag)
        if not key or not type_name.startswith("T"):
            continue
        records.append(_native_object_from_element(element, key, type_name))
    return tuple(sorted(records, key=lambda item: item.id))


def _parse_references(root: ET.Element) -> tuple[tuple[str, str, str], ...]:
    references = []
    for element in root.iter():
        source = element.attrib.get("key")
        if not source:
            continue
        for role, target in element.attrib.items():
            if role == "ref" or role.endswith("_ref"):
                references.append((source, role, target))
    return tuple(sorted(references))
```

- [ ] **Step 5: Run focused and full tests**

Run: `python -m unittest tests.unit.test_jmdl_archive -v`

Expected: 2 tests PASS.

Run: `python -m unittest discover -s tests -v`

Expected: all offline tests PASS.

- [ ] **Step 6: Commit the archive adapter**

```text
git add src/jmag_skill/jmdl_archive.py tests/fixtures/jmdl_minimal.xml tests/unit/test_jmdl_archive.py
git commit -m "feat: inspect JMDL archives read only"
```

---

### Task 3: Expression Tokenization and Dependency Graph

**Files:**
- Create: `src/jmag_skill/jmdl_graph.py`
- Test: `tests/unit/test_jmdl_graph.py`

**Interfaces:**
- Consumes: `Parameter`, `GraphEdge`, and `Diagnostic` from Task 1.
- Produces: `tokenize_expression(expression: str) -> tuple[str, ...]`; `build_parameter_graph(parameters: tuple[Parameter, ...]) -> GraphResult`; `GraphResult.edges`, `.diagnostics`, and `.dependencies`.

- [ ] **Step 1: Write failing graph tests**

```python
import unittest

from jmag_skill.jmdl_graph import build_parameter_graph, tokenize_expression
from jmag_skill.jmdl_model import Parameter


class JmdlGraphTests(unittest.TestCase):
    def test_tokenizes_fixture_expressions_and_builds_dependencies(self):
        self.assertEqual(tokenize_expression("Rso-dyoke-hslot-hso-hwedge"), ("Rso", "-", "dyoke", "-", "hslot", "-", "hso", "-", "hwedge"))
        parameters = (
            Parameter("Rso", "116.5", 116.5, ()),
            Parameter("dyoke", "19", 19, ()),
            Parameter("hslot", "16", 16, ()),
            Parameter("hso", "1", 1, ()),
            Parameter("hwedge", "1.2", 1.2, ()),
            Parameter("Rsi", "Rso-dyoke-hslot-hso-hwedge", 79.3, ()),
            Parameter("airgap", "0.8", 0.8, ()),
            Parameter("Rro", "Rsi-airgap", 78.5, ()),
        )
        result = build_parameter_graph(parameters)
        self.assertEqual(result.dependencies["Rro"], ("Rsi", "airgap"))
        self.assertIn("Rso", result.transitive_dependencies("Rro"))

    def test_reports_cycles_and_undefined_names_without_evaluating_code(self):
        parameters = (
            Parameter("a", "b+missing", None, ()),
            Parameter("b", "a", None, ()),
            Parameter("danger", "__import__('os')", None, ()),
        )
        result = build_parameter_graph(parameters)
        self.assertEqual({d.code for d in result.diagnostics}, {"expression-cycle", "undefined-variable", "unsupported-expression"})
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.unit.test_jmdl_graph -v`

Expected: FAIL because `jmdl_graph` does not exist.

- [ ] **Step 3: Implement tokenization and graph traversal**

```python
TOKEN = re.compile(r"(?:\d+(?:\.\d+)?)|(?:[A-Za-z_]\w*)|(?:[-+*/()])")


def tokenize_expression(expression: str) -> tuple[str, ...]:
    tokens = tuple(TOKEN.findall(expression))
    compact = re.sub(r"\s+", "", expression)
    if "".join(tokens) != compact:
        raise ValueError(f"unsupported expression syntax: {expression}")
    return tokens


@dataclass(frozen=True)
class GraphResult:
    dependencies: dict[str, tuple[str, ...]]
    edges: tuple[GraphEdge, ...]
    diagnostics: tuple[Diagnostic, ...]

    def transitive_dependencies(self, name: str) -> tuple[str, ...]:
        found: set[str] = set()
        stack = list(self.dependencies.get(name, ()))
        while stack:
            current = stack.pop()
            if current in found:
                continue
            found.add(current)
            stack.extend(self.dependencies.get(current, ()))
        return tuple(sorted(found))
```

Complete `build_parameter_graph` with a color-marked depth-first search for cycles. Treat identifiers absent from the parameter-name set as undefined. Catch tokenization `ValueError` and emit `unsupported-expression`; never call `eval`, `exec`, `ast.literal_eval`, or import a named function from the expression.

- [ ] **Step 4: Run focused and full tests**

Run: `python -m unittest tests.unit.test_jmdl_graph -v`

Expected: 2 tests PASS.

Run: `python -m unittest discover -s tests -v`

Expected: all offline tests PASS.

- [ ] **Step 5: Commit the graph service**

```text
git add src/jmag_skill/jmdl_graph.py tests/unit/test_jmdl_graph.py
git commit -m "feat: build JMDL parameter graph"
```

---

### Task 4: Reference Resolution and Native Diagnostics

**Files:**
- Create: `src/jmag_skill/jmdl_analysis.py`
- Test: `tests/unit/test_jmdl_analysis.py`

**Interfaces:**
- Consumes: `ArchiveSnapshot` from Task 2 and `GraphResult` from Task 3.
- Produces: `AnalysisResult`; `analyze_snapshot(snapshot: ArchiveSnapshot) -> AnalysisResult`; `resolve_references(snapshot: ArchiveSnapshot) -> tuple[GraphEdge, ...]`.

- [ ] **Step 1: Write failing reference and diagnostic tests**

```python
import unittest

from jmag_skill.jmdl_analysis import analyze_snapshot
from jmag_skill.jmdl_archive import ArchiveSnapshot
from jmag_skill.jmdl_model import Evidence, NativeObject, Parameter


class JmdlAnalysisTests(unittest.TestCase):
    def test_resolves_pattern_targets_and_reports_missing_duplicate_and_invalid_objects(self):
        snapshot = ArchiveSnapshot(
            filename="sample.jmdl", size=1, sha256="abc",
            versions={"SaveVersion": 251}, original_version=210, saved_version=251,
            members=("modeller_project.xml",), dat_members=(),
            objects=(
                NativeObject("10", "TSketch", "same", None, True, False, True, Evidence("modeller_project.xml", "key:10"), references=("20", "missing")),
                NativeObject("20", "TRegion", "same", "10", False, False, True, Evidence("modeller_project.xml", "key:20")),
            ),
            parameters=(Parameter("Slot_Number", "54", 54, ()),),
            raw_references=(("10", "target", "20"), ("10", "target", "missing")),
        )
        result = analyze_snapshot(snapshot)
        self.assertIn(("10", "20", "native-reference"), {(e.source, e.target, e.kind) for e in result.relationships})
        self.assertEqual({d.code for d in result.diagnostics}, {"duplicate-name", "invalid-object", "missing-reference"})
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python -m unittest tests.unit.test_jmdl_analysis -v`

Expected: FAIL because `jmdl_analysis` does not exist.

- [ ] **Step 3: Implement deterministic reference resolution and validators**

```python
@dataclass(frozen=True)
class AnalysisResult:
    graph: GraphResult
    relationships: tuple[GraphEdge, ...]
    diagnostics: tuple[Diagnostic, ...]
    semantic_hypotheses: tuple[SemanticHypothesis, ...] = ()


def resolve_references(snapshot: ArchiveSnapshot) -> tuple[GraphEdge, ...]:
    ids = {obj.id for obj in snapshot.objects}
    edges = [GraphEdge(source, target, "native-reference")
             for source, _role, target in snapshot.raw_references if target in ids]
    return tuple(sorted(edges, key=lambda edge: (edge.source, edge.target, edge.kind)))


def analyze_snapshot(snapshot: ArchiveSnapshot) -> AnalysisResult:
    graph = build_parameter_graph(snapshot.parameters)
    relationships = resolve_references(snapshot)
    diagnostics = list(graph.diagnostics)
    diagnostics.extend(_missing_reference_diagnostics(snapshot))
    diagnostics.extend(_duplicate_name_diagnostics(snapshot.objects))
    diagnostics.extend(_invalid_object_diagnostics(snapshot.objects))
    return AnalysisResult(graph, relationships, tuple(sorted(diagnostics, key=lambda item: (item.code, item.object_ids, item.message))))
```

Add `_parameter_consumer_edges` by inspecting normalized object properties that contain expression text. Emit edge kinds `parameter-property` and `parameter-constraint`; never search arbitrary raw XML outside the archive adapter.

- [ ] **Step 4: Run focused and full tests**

Run: `python -m unittest tests.unit.test_jmdl_analysis -v`

Expected: 1 test PASS.

Run: `python -m unittest discover -s tests -v`

Expected: all offline tests PASS.

- [ ] **Step 5: Commit native analysis**

```text
git add src/jmag_skill/jmdl_analysis.py tests/unit/test_jmdl_analysis.py
git commit -m "feat: diagnose JMDL object references"
```

---

### Task 5: Evidence-Based Semantic Classifier

**Files:**
- Modify: `src/jmag_skill/jmdl_analysis.py`
- Modify: `tests/unit/test_jmdl_analysis.py`

**Interfaces:**
- Consumes: normalized native objects, relationships, graph edges, and diagnostics.
- Produces: `classify_semantics(snapshot: ArchiveSnapshot, analysis: AnalysisResult) -> tuple[SemanticHypothesis, ...]` and populated `AnalysisResult.semantic_hypotheses`.

- [ ] **Step 1: Add failing certainty and evidence tests**

```python
def test_sketch_two_is_only_an_unconfirmed_hypothesis(self):
    snapshot = sample_snapshot_with_sketch_two_and_patterns()
    result = analyze_snapshot(snapshot)
    hypothesis = next(item for item in result.semantic_hypotheses if item.object_id == "11")
    self.assertEqual(hypothesis.semantic_type, "winding-related-geometry")
    self.assertIn(hypothesis.confidence, {"low", "medium"})
    self.assertFalse(hypothesis.user_confirmed)
    self.assertGreaterEqual(len(hypothesis.evidence), 2)

def test_name_or_position_alone_never_produces_high_confidence(self):
    snapshot = snapshot_with_named_sketch_only("winding", object_id="90")
    result = analyze_snapshot(snapshot)
    hypothesis = next(item for item in result.semantic_hypotheses if item.object_id == "90")
    self.assertNotEqual(hypothesis.confidence, "high")
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m unittest tests.unit.test_jmdl_analysis.JmdlAnalysisTests.test_sketch_two_is_only_an_unconfirmed_hypothesis -v`

Expected: FAIL because no semantic hypothesis exists.

- [ ] **Step 3: Implement named deterministic rules and confidence caps**

```python
RULES = (
    ("name-stator-yoke", lambda obj, _ctx: obj.name == "Stator_yoke", "stator-yoke", 2),
    ("name-stator-teeth", lambda obj, _ctx: obj.name == "Stator_teeth", "stator-teeth", 2),
    ("name-rotor", lambda obj, _ctx: obj.name == "rotor", "rotor-core-geometry", 2),
    ("patterned-conductor-shape", _has_linear_then_radial_pattern, "winding-related-geometry", 2),
    ("winding-name-clue", _has_winding_name_clue, "winding-related-geometry", 1),
)


def _has_winding_name_clue(obj: NativeObject, _context: dict[str, object]) -> bool:
    return bool(obj.name and any(token in obj.name.lower() for token in ("winding", "coil", "conductor")))


def _has_linear_then_radial_pattern(obj: NativeObject, context: dict[str, object]) -> bool:
    children = context["children"].get(obj.id, [])
    child_types = {child.type for child in children}
    return "TRegionLinearPattern" in child_types and "TRegionRadialPattern" in child_types


def classify_semantics(snapshot: ArchiveSnapshot, analysis: AnalysisResult) -> tuple[SemanticHypothesis, ...]:
    children: dict[str, list[NativeObject]] = {}
    for item in snapshot.objects:
        if item.parent_id:
            children.setdefault(item.parent_id, []).append(item)
    context = {"children": children, "relationships": analysis.relationships}
    matches: dict[tuple[str, str], list[tuple[str, int]]] = {}
    for obj in snapshot.objects:
        for rule_id, predicate, semantic_type, weight in RULES:
            if predicate(obj, context):
                matches.setdefault((obj.id, semantic_type), []).append((rule_id, weight))
    hypotheses = []
    for (object_id, semantic_type), evidence in sorted(matches.items()):
        score = sum(weight for _rule_id, weight in evidence)
        rule_ids = tuple(sorted(rule_id for rule_id, _weight in evidence))
        structural_count = sum(not rule_id.startswith("name-") and rule_id != "winding-name-clue" for rule_id in rule_ids)
        confidence = "high" if score >= 6 and structural_count >= 3 else "medium" if score >= 3 else "low"
        if any(rule_id.startswith("name-") or rule_id == "winding-name-clue" for rule_id in rule_ids) and structural_count < 3:
            confidence = "medium" if score >= 3 else "low"
        hypotheses.append(SemanticHypothesis(object_id, semantic_type, confidence, rule_ids, False))
    return tuple(hypotheses)
```

Add this referential-integrity assertion to `test_jmdl_analysis.py`:

```python
def test_every_hypothesis_targets_an_existing_native_object(self):
    snapshot = sample_snapshot_with_sketch_two_and_patterns()
    result = analyze_snapshot(snapshot)
    object_ids = {item.id for item in snapshot.objects}
    self.assertTrue(result.semantic_hypotheses)
    self.assertTrue(all(item.object_id in object_ids for item in result.semantic_hypotheses))
```

- [ ] **Step 4: Run focused and full tests**

Run: `python -m unittest tests.unit.test_jmdl_analysis -v`

Expected: all analysis tests PASS.

Run: `python -m unittest discover -s tests -v`

Expected: all offline tests PASS.

- [ ] **Step 5: Commit the classifier**

```text
git add src/jmag_skill/jmdl_analysis.py tests/unit/test_jmdl_analysis.py
git commit -m "feat: classify JMDL geometry with evidence"
```

---

### Task 6: Discovery Orchestrator and Deterministic Renderers

**Files:**
- Create: `src/jmag_skill/jmdl_discovery.py`
- Create: `src/jmag_skill/jmdl_render.py`
- Create: `tests/unit/test_jmdl_render.py`
- Create: `tests/fixtures/sample_inventory.golden.json`
- Create: `tests/fixtures/sample_report.golden.md`

**Interfaces:**
- Consumes: `read_jmdl`, `analyze_snapshot`, and all domain records.
- Produces: `discover_jmdl(path: Path) -> Inventory`; `render_inventory(inventory: Inventory) -> str`; `render_report(inventory: Inventory) -> str`; `write_outputs(inventory, inventory_path, report_path, force=False) -> None`.

- [ ] **Step 1: Write failing deterministic rendering tests**

```python
import json
import tempfile
import unittest
from pathlib import Path

from jmag_skill.jmdl_discovery import write_outputs
from jmag_skill.jmdl_render import render_inventory, render_report


class JmdlRenderTests(unittest.TestCase):
    def test_json_and_markdown_are_deterministic(self):
        inventory = representative_inventory()
        self.assertEqual(render_inventory(inventory), render_inventory(inventory))
        self.assertEqual(json.loads(render_inventory(inventory))["schema_version"], "1.0")
        report = render_report(inventory)
        self.assertIn("## Uncertain classifications", report)
        self.assertIn("Sketch.2", report)
        self.assertIn("user confirmation required", report.lower())

    def test_output_set_is_atomic_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            inventory_path = Path(tmp) / "inventory.json"
            report_path = Path(tmp) / "report.md"
            inventory_path.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                write_outputs(representative_inventory(), inventory_path, report_path, force=False)
            self.assertEqual(inventory_path.read_text(encoding="utf-8"), "existing")
            self.assertFalse(report_path.exists())
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest tests.unit.test_jmdl_render -v`

Expected: FAIL because discovery and rendering modules do not exist.

- [ ] **Step 3: Implement discovery and rendering**

```python
def discover_jmdl(path: Path) -> Inventory:
    snapshot = read_jmdl(path)
    analysis = analyze_snapshot(snapshot)
    return Inventory(
        schema_version="1.0",
        source=snapshot.source_metadata(),
        native_objects=snapshot.objects,
        parameters=tuple(replace(param, dependencies=analysis.graph.dependencies.get(param.name, ())) for param in snapshot.parameters),
        dependency_graph=analysis.graph.edges,
        relationships=analysis.relationships,
        geometry=_geometry_summary(snapshot.objects),
        diagnostics=analysis.diagnostics,
        semantic_hypotheses=analysis.semantic_hypotheses,
    )


def render_inventory(inventory: Inventory) -> str:
    return json.dumps(inventory.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
```

Implement `render_report` with the nine approved sections and an evidence/confidence line for every hypothesis. Implement `write_outputs` by prechecking destinations, rendering both strings, writing sibling temporary files with UTF-8/newline normalization, and replacing destinations only after both writes succeed. On failure, remove only temporary files created by the current call.

- [ ] **Step 4: Create and assert golden snapshots**

Generate the fixture snapshots from `representative_inventory()` and add assertions:

```python
self.assertEqual(render_inventory(inventory), Path("tests/fixtures/sample_inventory.golden.json").read_text(encoding="utf-8"))
self.assertEqual(render_report(inventory), Path("tests/fixtures/sample_report.golden.md").read_text(encoding="utf-8"))
```

The normalized golden data must include 41 parameters and the confirmed fixture relationships, but must exclude the source absolute path and volatile timestamps.

- [ ] **Step 5: Run focused and full tests**

Run: `python -m unittest tests.unit.test_jmdl_render -v`

Expected: all rendering tests PASS.

Run: `python -m unittest discover -s tests -v`

Expected: all offline tests PASS.

- [ ] **Step 6: Commit discovery and rendering**

```text
git add src/jmag_skill/jmdl_discovery.py src/jmag_skill/jmdl_render.py tests/unit/test_jmdl_render.py tests/fixtures/sample_inventory.golden.json tests/fixtures/sample_report.golden.md
git commit -m "feat: render JMDL discovery reports"
```

---

### Task 7: Reusable CLI Command and Exit Codes

**Files:**
- Modify: `src/jmag_skill/cli.py`
- Create: `tests/integration/test_jmdl_cli.py`

**Interfaces:**
- Consumes: `discover_jmdl`, `render_inventory`, `write_outputs`, and `DiscoveryError.exit_code`.
- Produces: public `jmag-skill inspect-jmdl SOURCE [--inventory PATH] [--report PATH] [--force]` behavior.

- [ ] **Step 1: Write failing CLI tests**

```python
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


class JmdlCliTests(unittest.TestCase):
    def test_stdout_mode_emits_json_and_does_not_create_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = build_minimal_jmdl(Path(tmp))
            completed = subprocess.run(
                [sys.executable, "-m", "jmag_skill.cli", "inspect-jmdl", str(source)],
                capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "src"},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["source"]["filename"], source.name)
            self.assertEqual({path.name for path in Path(tmp).iterdir()}, {source.name})

    def test_bad_zip_returns_three_and_leaves_no_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "bad.jmdl"
            source.write_bytes(b"bad")
            inventory = Path(tmp) / "inventory.json"
            completed = subprocess.run(
                [sys.executable, "-m", "jmag_skill.cli", "inspect-jmdl", str(source), "--inventory", str(inventory)],
                capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "src"},
            )
            self.assertEqual(completed.returncode, 3)
            self.assertFalse(inventory.exists())
```

Add cases for missing input/output-exists exit 2, unsupported structure exit 4, two explicit outputs, and `--force` affecting only output files.

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest tests.integration.test_jmdl_cli -v`

Expected: FAIL because `inspect-jmdl` is not a known command.

- [ ] **Step 3: Register the parser and thin dispatch branch**

```python
inspect_jmdl = sub.add_parser("inspect-jmdl")
inspect_jmdl.add_argument("source", type=Path)
inspect_jmdl.add_argument("--inventory", type=Path)
inspect_jmdl.add_argument("--report", type=Path)
inspect_jmdl.add_argument("--force", action="store_true")
```

```python
if args.command == "inspect-jmdl":
    from .jmdl_discovery import discover_jmdl, write_outputs
    from .jmdl_model import DiscoveryError, UsageDiscoveryError
    from .jmdl_render import render_inventory
    try:
        inventory = discover_jmdl(args.source)
        if args.inventory or args.report:
            write_outputs(inventory, args.inventory, args.report, force=args.force)
        else:
            print(render_inventory(inventory), end="")
        return 0
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except DiscoveryError as exc:
        print(str(exc), file=sys.stderr)
        return exc.exit_code
```

Convert missing-source `FileNotFoundError` into `UsageDiscoveryError` inside `discover_jmdl`. Ensure `--force` is ignored in stdout mode and never passed to archive reading.

- [ ] **Step 4: Run focused and full tests**

Run: `python -m unittest tests.integration.test_jmdl_cli -v`

Expected: all CLI tests PASS.

Run: `python -m unittest discover -s tests -v`

Expected: all offline tests PASS.

- [ ] **Step 5: Commit the public command**

```text
git add src/jmag_skill/cli.py tests/integration/test_jmdl_cli.py
git commit -m "feat: add inspect-jmdl command"
```

---

### Task 8: Real Fixture Snapshot, Required Reports, and Final Verification

**Files:**
- Create: `tests/integration/test_jmdl_sample.py`
- Create: `docs/jmdl_format_observations.md`
- Create: `artifacts/sample_inventory.json`
- Create: `artifacts/sample_report.md`
- Create: `docs/architecture.md`
- Create: `docs/jmag_api_evidence.md`
- Create: `docs/implementation_plan.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the complete `inspect-jmdl` command and the local `Test_JMAG_Model_Files.jmdl`.
- Produces: all user-requested Phase 1 artifacts, API evidence ledger, milestones, and final regression evidence.

- [ ] **Step 1: Write the real-fixture acceptance test**

```python
import hashlib
import unittest
from pathlib import Path

from jmag_skill.jmdl_discovery import discover_jmdl


SOURCE = Path(__file__).parents[2] / "Test_JMAG_Model_Files.jmdl"


@unittest.skipUnless(SOURCE.is_file(), "local supplied JMDL fixture is not present")
class JmdlSampleTests(unittest.TestCase):
    def test_required_sample_facts_and_source_immutability(self):
        before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        inventory = discover_jmdl(SOURCE)
        after = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        payload = inventory.to_dict()
        self.assertEqual(before, after)
        self.assertEqual(payload["source"]["versions"]["SaveVersion"], 251)
        self.assertEqual(len(payload["parameters"]), 41)
        names = {obj["name"] for obj in payload["native_objects"]}
        self.assertTrue({"Stator_yoke", "Stator_teeth", "Sketch.2", "rotor"}.issubset(names))
        expressions = {item["name"]: item["expression"] for item in payload["parameters"]}
        self.assertEqual(expressions["Rsi"], "Rso-dyoke-hslot-hso-hwedge")
        self.assertEqual(expressions["Rro"], "Rsi-airgap")
        sketch_two = [item for item in payload["semantic_hypotheses"] if item["object_id"] == object_id_for(payload, "Sketch.2")]
        self.assertTrue(sketch_two)
        self.assertNotEqual(sketch_two[0]["confidence"], "high")
        self.assertFalse(sketch_two[0]["user_confirmed"])
```

- [ ] **Step 2: Run the acceptance test and verify RED**

Run: `python -m unittest tests.integration.test_jmdl_sample -v`

Expected: FAIL on the first incomplete required fact, establishing the remaining parser gap.

- [ ] **Step 3: Close fixture-specific parser gaps without leaking them downstream**

Adjust only `jmdl_archive.py` private extraction helpers for observed JMDL 25.1 structures. For each new XML path or attribute:

```python
def _attribute(element: ET.Element, names: tuple[str, ...]) -> str | None:
    for name in names:
        if name in element.attrib:
            return element.attrib[name]
    return None
```

Add a focused archive test using a minimal XML fragment before every adjustment. Do not add raw XML navigation to graph, analysis, rendering, or CLI modules.

- [ ] **Step 4: Generate and verify the requested artifacts**

Run:

```text
jmag-skill inspect-jmdl Test_JMAG_Model_Files.jmdl --inventory artifacts/sample_inventory.json --report artifacts/sample_report.md
```

Expected: exit 0; both files created; source SHA-256 remains `D14A8D5898E28D3D00E62F4E6190E12B9DFB63991B01D1B2B1669746E577B2A9`.

Verify with a short standard-library script that the inventory reports version 251, 41 parameters, the four required sketches, both required parameter expressions, and both circular-pattern expression relationships.

- [ ] **Step 5: Write the required evidence documents**

`docs/jmdl_format_observations.md` must record the 48-entry archive, version fields, typed key/reference object model, DAT filename references, readable DAT observations, and the explicit prohibition on direct XML writes.

`docs/architecture.md` must describe the archive adapter, future live adapter, domain model, graph, classifier, validator, future transactional mutation engine, future feature/template library, and CLI/GUI boundaries, marking future components unimplemented.

`docs/jmag_api_evidence.md` must contain a row for every operation requested by the user. Populate these three verified rows from the already retrieved installed Help:

```text
GeomDocument::GetDesignTable() | Modeller/classGeomDocument.html#a95cdb3d9ea07f7b72dc2c5abab85082b | verified by installed wrapper/help
Application::CreateGeometryEditor(bool askForSave = true) | Designer/classApplication.html#a46d83dc18600577f049c1cb9650439bb | verified by installed wrapper/help
Model::ChangeCadLinkToGeometryEditor() | Designer/classModel.html#a632db3ccdd2ee1aa1675deb41f698ee0 | verified by installed wrapper/help
```

Mark every other operation `not yet found` unless installed wrapper or anchored Help evidence was actually obtained. Do not infer methods from XML names.

`docs/implementation_plan.md` must summarize completed Phase 1 milestones and independently testable next-phase milestones with acceptance criteria; it must not claim mutation or GUI work is complete.

Update `README.md` with one concise `inspect-jmdl` example and the read-only/experimental archive-format warning.

- [ ] **Step 6: Run complete verification**

Run: `python -m unittest discover -s tests -v`

Expected: every offline test PASS; the real JMAG lifecycle test remains skipped unless explicitly enabled; the real JMDL acceptance test runs because the local fixture is present.

Run: `python -m jmag_skill.cli inspect-jmdl Test_JMAG_Model_Files.jmdl`

Expected: exit 0 and valid JSON on stdout; no new file is created.

Run: `git diff --check`

Expected: no output and exit 0.

Run a final source hash check.

Expected: `D14A8D5898E28D3D00E62F4E6190E12B9DFB63991B01D1B2B1669746E577B2A9`.

- [ ] **Step 7: Review scope and commit final Phase 1 deliverables**

Confirm that `git diff --name-only` contains no modification under `src/jmag_functions`, `references/function-catalog.json`, promotion records, or the binary source JMDL.

```text
git add README.md src/jmag_skill/jmdl_archive.py tests/unit/test_jmdl_archive.py tests/integration/test_jmdl_sample.py docs/jmdl_format_observations.md artifacts/sample_inventory.json artifacts/sample_report.md docs/architecture.md docs/jmag_api_evidence.md docs/implementation_plan.md
git commit -m "docs: deliver JMDL discovery evidence"
```

Stop after the commit. Report created files, confirmed findings, uncertain findings, APIs still requiring evidence, and risks that could block the next phase. Do not run JMAG, inspect a promotion candidate, implement GUI, or implement mutation.

---

## Plan Self-Review Results

- Spec coverage: every approved architecture, inventory, classification, CLI, failure-policy, testing, documentation, and stop-boundary requirement maps to Tasks 1-8.
- Scope: the plan implements one cohesive read-only discovery vertical slice; live JMAG, mutation, templates, and GUI remain documented boundaries only.
- Type consistency: archive records feed graph/analysis, analysis feeds `Inventory`, and render/CLI consume only `Inventory`; the same function and field names are used throughout.
- Safety: source hashing, no extraction, output prechecks, atomic temporary writes, and explicit exclusions are tested.
- Evidence: only the three already retrieved Help topics are marked verified; all other future API operations default to `not yet found`.
