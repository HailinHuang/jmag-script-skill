# Read-Only JMDL Discovery Design

## Purpose

Phase 1 adds a reusable, offline command that inspects a supplied JMAG Designer 25.1 `.jmdl` archive and produces a deterministic native-object inventory plus a human-readable evidence report. It establishes boundaries that can later support a live Geometry Editor adapter and safe mutation workflow without treating undocumented XML or DAT records as a supported write API.

The public command is:

```text
jmag-skill inspect-jmdl SOURCE [--inventory PATH] [--report PATH] [--force]
```

With no output option, the command writes deterministic inventory JSON to standard output. It writes files only for explicitly supplied output paths. `--force` may replace only those requested inventory or report files; it never modifies `SOURCE`.

## Scope and Safety

Phase 1 may:

- open the source as a ZIP archive in read-only mode;
- verify ZIP integrity and parse contained XML;
- index DAT filenames and references without reverse-engineering their private record format;
- construct native-object, parameter, expression, reference, and dependency inventories;
- apply deterministic diagnostic and semantic-suggestion rules;
- create repository reports, snapshots, schemas, tests, and documentation.

Phase 1 must not:

- load or save a document through JMAG;
- mutate XML, DAT, a Geometry Editor document, or the source JMDL;
- run a study, delete results, rebuild geometry, or check intersections;
- implement GUI or model-mutation operations;
- add or promote a function in `src/jmag_functions`, the stable catalog, or project-sync capability;
- classify `Sketch.2` as a winding with certainty.

The implementation records the source SHA-256 before analysis and verifies it is unchanged after every end-to-end test.

## Confirmed Fixture Evidence

The supplied `Test_JMAG_Model_Files.jmdl` is a 530,280-byte ZIP container with 48 entries. Its CRC integrity check succeeds. The archive contains `info.txt`, `modeller_project.xml`, and 46 `modeller_data*.dat` files.

The sample confirms:

- `Version`, `SaveVersion`, and `CreationVersion` 251;
- XML `original_version` 210 and `saved_version` 251;
- 41 design parameters represented by 41 `TParametricEquation` instances;
- four native sketch instances named `Stator_yoke`, `Stator_teeth`, `Sketch.2`, and `rotor`;
- `Rsi = Rso-dyoke-hslot-hso-hwedge`;
- `Rro = Rsi-airgap`;
- parameter-driven circular-pattern relationships `angle = 360/Slot_Number` and `instance = Slot_Number/6` for `Stator_yoke` and `Stator_teeth`;
- saved numeric angle and instance values for the `Sketch.2` and `rotor` radial patterns, with empty expression fields;
- native sketch, vertex, line, arc, circle, pattern, region, and constraint records connected through typed keys and references.

DAT content is treated as cached or referenced native data. Readable identifiers observed inside DAT files support that conclusion, but their private field structure is not a production contract.

## Architecture

### Read-only archive adapter

`src/jmag_skill/jmdl_archive.py` owns every dependency on the undocumented archive layout. It:

- opens ZIP files without extraction;
- validates CRCs;
- locates version metadata and the project XML;
- indexes archive members and DAT references;
- parses XML with the Python standard library;
- converts XML elements into neutral raw records containing source evidence.

No other module navigates raw XML paths or interprets DAT filenames. Unsupported records are preserved as typed raw objects and diagnostics rather than discarded.

### Domain model

`src/jmag_skill/jmdl_model.py` defines immutable or value-oriented records for:

- archive metadata and evidence locations;
- native objects and parent/child relationships;
- parameters, expressions, values, and tokens;
- properties, constraints, sketches, regions, and patterns;
- typed references and reference-resolution results;
- diagnostics;
- semantic part and feature hypotheses.

Stable internal IDs derive from native keys where available and deterministic structural paths otherwise. Input order is never used as an implicit identity.

### Dependency graph service

`src/jmag_skill/jmdl_graph.py` tokenizes expressions and constructs directed edges for:

```text
parameter -> expression -> property/constraint -> feature -> semantic hypothesis
```

It detects undefined variables and cycles without evaluating arbitrary code. Tokenization recognizes identifiers, numeric literals, operators, parentheses, and known expression syntax required by the fixture. Unknown syntax is retained and diagnosed.

### Rule-based classifier and validator

`src/jmag_skill/jmdl_analysis.py` contains deterministic, independently testable rules. The validator reports invalid objects, expression errors, unresolved references, duplicate names, cycles, and undefined variables.

Semantic classifications are hypotheses with:

- proposed semantic type;
- confidence level;
- positive and negative evidence;
- contributing rule identifiers;
- native object references;
- explicit user-confirmation status.

Object position, nearby parameter names, or a single naming clue can support a hypothesis but cannot yield high confidence alone. In particular, `Sketch.2` is reported only as possible winding-related geometry, with low or medium confidence depending on combined evidence.

### Rendering and CLI

`src/jmag_skill/jmdl_render.py` serializes the inventory and renders the Markdown report. Serialization uses stable ordering for objects, edges, diagnostics, and report sections. Timestamps, absolute source paths, and machine-specific data are excluded from golden snapshots.

`src/jmag_skill/cli.py` only parses arguments, calls the discovery service, and maps domain failures to exit codes. The CLI does not contain parsing, classification, or graph logic.

### Future boundaries

The following components are documented but not implemented in Phase 1:

- a JMAG Geometry Editor live adapter that maps Help-verified native objects into the shared domain model;
- a transactional mutation engine with preconditions, rollback, and new-target-file semantics;
- a feature/template library;
- GUI front ends.

These components must depend on the domain contract, not on raw archive XML.

## Inventory Contract

`artifacts/sample_inventory.json` conforms to `schemas/jmdl-inventory.schema.json` and contains these top-level sections:

- `schema_version`;
- `source`: filename, size, SHA-256, ZIP status, versions, and archive members;
- `native_objects`: deterministic object tree and flat typed index;
- `parameters`: names, raw expressions, parsed tokens, saved values, and dependency status;
- `dependency_graph`: typed nodes and edges;
- `relationships`: parameter-to-property and parameter-to-constraint links;
- `geometry`: sketches, regions, patterns, and constraints;
- `diagnostics`: invalid objects, expression errors, unresolved references, duplicates, cycles, undefined variables, and unsupported structures;
- `semantic_hypotheses`: evidence-backed part and feature suggestions with confidence and confirmation status.

Every reported native fact includes an evidence pointer identifying its archive member and a stable XML element path or native key. Semantic hypotheses cite the native facts and rules that produced them.

## Human-Readable Report

`artifacts/sample_report.md` contains:

1. source integrity and version summary;
2. native object and geometry overview;
3. design parameters and dependency findings;
4. parameter-to-property and constraint relationships;
5. semantic part and feature hypotheses;
6. uncertain classifications requiring user confirmation;
7. errors, warnings, and missing references;
8. parameterisation-quality observations and proposed improvements;
9. limitations of archive-only evidence.

Recommendations remain separate from confirmed facts. Each classification includes confidence and evidence.

## Failure Policy

The command uses these exit codes:

- `0`: analysis completed; structured warnings or uncertain hypotheses may be present;
- `2`: invalid arguments, missing input, or an output path already exists without `--force`;
- `3`: bad ZIP, CRC failure, or unreadable project XML;
- `4`: a required archive structure is unsupported or absent, preventing a trustworthy inventory.

Parseable missing references, invalid objects, duplicate names, expression errors, cycles, and undefined variables are inventory diagnostics and do not by themselves make the command fail.

The implementation builds and renders all outputs in memory, validates them, writes sibling temporary files, and replaces requested destinations only after all temporary writes succeed. On failure it removes only its own temporary files. It never deletes or renames the source.

## JMAG API Evidence Boundary

The Phase 1 command uses no JMAG API. The initial Help search found no stable reusable capability. One bounded Help retrieval returned three anchored topics:

- `GeomDocument::GetDesignTable()` — verified by installed JMAG 25.1 Help;
- `Application::CreateGeometryEditor(bool askForSave = true)` — verified by installed JMAG 25.1 Help;
- `Model::ChangeCadLinkToGeometryEditor()` — verified by installed JMAG 25.1 Help, but not used in Phase 1.

All other operations required for a future live adapter or mutation engine remain `not yet found` unless later verified by installed wrapper signatures or anchored Help. Observed XML names never establish an API method or property name.

`docs/jmag_api_evidence.md` will list each required operation, exact class and signature when known, Help source, and one of these statuses:

- verified by installed wrapper/help;
- observed but unverified;
- not yet found.

No iteration may retrieve more than three closely related anchored Help topics.

## Testing Strategy

All offline tests use `unittest` and standard Python; JMAG installation is not required.

### Archive tests

- valid ZIP and CRC integrity;
- missing, corrupt, or duplicate project XML;
- version extraction;
- DAT member and reference indexing;
- proof that the source hash remains unchanged.

### XML and reference tests

- namespaced and non-namespaced XML parsing where encountered;
- native key indexing and parent/child construction;
- resolved, missing, duplicate, and wrong-type references;
- unsupported object preservation;
- deterministic ordering.

### Expression and graph tests

- tokenization of arithmetic and identifiers;
- the fixture expressions for `Rsi` and `Rro`;
- circular-pattern angle and instance relationships;
- transitive dependencies;
- cycle detection;
- undefined-variable detection;
- unknown-syntax diagnostics without code execution.

### Diagnostic and classification tests

- invalid objects and expression errors;
- duplicate-name diagnostics;
- evidence aggregation and confidence thresholds;
- explicit uncertainty for `Sketch.2`;
- absence of unsupported certainty claims.

### CLI and golden tests

- stdout JSON when no output option is supplied;
- explicit inventory and report paths;
- no overwrite without `--force`;
- exit-code mapping and no partial output;
- schema validation;
- golden inventory and report snapshots derived from the supplied fixture;
- unchanged source hash before and after execution.

The binary source model remains local and untracked unless the user explicitly authorizes committing it. Minimal synthetic archives and normalized snapshots provide repository test fixtures.

## Deliverables

Phase 1 produces:

- `docs/jmdl_format_observations.md`;
- `artifacts/sample_inventory.json`;
- `artifacts/sample_report.md`;
- `docs/architecture.md`;
- `docs/jmag_api_evidence.md`;
- `docs/implementation_plan.md`;
- the reusable `inspect-jmdl` command and its offline test suite;
- an inventory schema and minimal synthetic fixtures as needed by the tests.

After these deliverables and tests pass, work stops. Model mutation, GUI development, live JMAG integration, candidate inspection, and stable-capability promotion require separate authorization.
