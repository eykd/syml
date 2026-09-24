# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.12 [or NEEDS CLARIFICATION]
**Primary Dependencies**: Parsimonious (+ `regex`) [or NEEDS CLARIFICATION]
**Storage**: [if applicable, e.g., files, embedded DB or N/A]
**Testing**: pytest (+ pytest-bdd for acceptance) [or NEEDS CLARIFICATION]
**Target Platform**: [e.g., Linux/macOS CLI, library consumers or NEEDS CLARIFICATION]
**Project Type**: library [single/library/mobile - determines source structure]
**Performance Goals**: [domain-specific, e.g., parse throughput, memory ceiling or NEEDS CLARIFICATION]
**Constraints**: [domain-specific, e.g., document size limits, depth limits or NEEDS CLARIFICATION]
**Scale/Scope**: [domain-specific, e.g., grammar rules touched, document sizes or NEEDS CLARIFICATION]

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

[Gates determined based on constitution file]

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused paths and expand the chosen structure with
  real paths. The delivered plan must not include placeholder brackets.
-->

```text
src/syml/
├── parsers.py            # Parsimonious PEG grammar + SymlParser(NodeVisitor)
├── nodes.py               # SymlNode tree (ContainerNode, TextLeafNode, ...)
└── basetypes.py           # Source, Pos

tests/
└── [unit tests mirroring src/syml/**]

tests/acceptance/
└── test_us<nn>_<slug>.py  # pytest-bdd bindings, marked `acceptance`

specs/acceptance-specs/
└── US<NN>-<slug>.feature  # Gherkin scenarios consumed by tests/acceptance

tools/
└── [CLI / dev tooling, if any]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Acceptance Test Strategy

> **ATDD Outer Loop**: Each user story with acceptance scenarios in the spec will have a corresponding acceptance spec file created during `sp:05-tasks`. These files live in `specs/acceptance-specs/` and follow the GWT format consumed by the acceptance pipeline. Ralph's ATDD cycle depends on these files existing before `US<N>` tasks are processed.

| User Story | Acceptance Spec File                           | Bindings                              | Scenarios |
| ---------- | ----------------------------------------------- | -------------------------------------- | --------- |
| [US1: ...] | `specs/acceptance-specs/US<NN>-<slug>.feature`  | `tests/acceptance/test_us<nn>_<slug>.py` | [N]       |

**Pipeline**: pytest-bdd via `just acceptance`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation                  | Why Needed         | Simpler Alternative Rejected Because |
| --------------------------- | ------------------ | ------------------------------------- |
| [e.g., new runtime dependency] | [current need]  | [why the stdlib/existing deps are insufficient] |
| [e.g., new grammar rule]    | [specific problem] | [why existing grammar shape is insufficient]  |
