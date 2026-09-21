# Implementation Plan: syml 1.0 — Full Conformance to the SYML Specification

**Branch**: `001-syml-1-0-conformance` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-syml-1-0-conformance/spec.md`
**Beads**: epic `syml-x0m`, plan phase task `syml-x0m.1`

> Fenced examples in this document never carry a literal trailing space — the
> repository's `trailing-whitespace` pre-commit hook strips them. Where one is
> significant it is written `␠` (U+2420 SYMBOL FOR SPACE). See research.md R-05.

## Summary

Make the shipped parser, serializer, error taxonomy, and source-tracking surface
match `SYML-SPECIFICATION.md` in full, and leave `main` ready to release as
1.0.0. The audit found 27 of 53 specification examples passing across 21
verified gaps; this feature closes every one that is not explicitly deferred.

The approach is a **layered rebuild in dependency order**, not a scatter of
point fixes: pre-processing (§9.0) → lexing (§4.1) → tree building (§9.2–9.4) →
quoting (§4.7) → API and errors (§11) → source tracking and release (§10, §14).
Each layer's divergences contaminate the layers below it, so the order is
forced. Three structural moves carry most of the work:

1. **A real pre-processing stage** (`src/syml/preprocess.py`) producing a
   `Document` (original + normalized + `PositionMap`). BOM, CRLF/CR, the tab
   scan, LF-only line splitting, and original-text position recovery all land
   here, once.
2. **Per-line lexing as the entry point.** The `document` rule stays in the
   grammar for fidelity with §4.1/D16, but parsing splits on `\n` first and runs
   `grammar['line'].parse()` per physical line. This makes §5.1 rule 6 structural
   and gives the third-party-exception boundary exactly one meaning (R-09).
3. **`level` becomes the node's own column**, per §9's definition, instead of the
   line's indentation inherited through a recursive `set_level` (R-11).

Everything else — the `==` sibling rule, the closed-node rule, D11's baseline and
re-offer, duplicate keys at incorporation, `""` instead of `None`, the seven-class
taxonomy, `dumps`/`dump`, original-text `Pos` — sits on those three.

## Technical Context

**Language/Version**: Python ≥ 3.12 (`requires-python = ">=3.12"`)
**Primary Dependencies**: `parsimonious>=0.10,<0.11` (PEG). `regex>=2024.11.6`
is declared but unused by `src/`; this feature does not start using it — see
Constitution Check, principle V.
**Storage**: N/A (in-memory parsing library)
**Testing**: pytest (random order, 100% branch coverage gate at commit/CI),
pytest-bdd for acceptance (`just acceptance`), mypy strict over `src/`,
`tests/`, `tools/`, ruff preview with pydocstyle `D`.
**Target Platform**: library consumers on any CPython 3.12+ platform; published
to PyPI.
**Project Type**: library (`src/` layout, hatchling, `uv`).
**Performance Goals**: no regression beyond the same order of magnitude as
0.6.2. Per-line lexing replaces one whole-document parse with N line parses;
Parsimonious's cost is dominated by per-token work, so this is expected to be
roughly neutral. Not measured as an acceptance criterion — no FR or SC mentions
throughput.
**Constraints**: §13.4's implementation limits (max depth 500, max line 1 MiB,
max document 10 MiB) and `DocumentLimitError` are **deferred past 1.0** by
decision. Nesting past ~500 levels raises the host `RecursionError` and is
documented as a known limitation, not a defect.
**Scale/Scope**: ~530 lines of `src/`, of which every module is touched; one new
module each for pre-processing, quoting, and serialization; 20 FRs; 9 user
stories; 70 acceptance scenarios; 53+ extracted specification examples.

### Constraints carried from the brainstorm

- The specification text labelled v1.1 **is** the 1.0 specification; relabel at
  release, folding §14's two rows into one.
- `dumps`/`dump` are in scope — a 1.0 that cannot round-trip is half-conforming.
- D17 stands: no root-scalar quoting.
- Clean break from 0.6.2, documented; no bridge release, no compatibility flags.
- All §13.4 limits deferred.
- The specification is **open** during implementation (FR-019 amends the
  constitution to permit it); edits land in the same commit as the behaviour
  they change.
- Source positions are in the **original** text (FR-013).
- `load()` accepts both text and binary streams (FR-010).

**No NEEDS CLARIFICATION remains.** The spec carried eight open items into
planning (six from the brainstorm's "Deferred to Planning" list, plus
`EncodingError`'s parent and the acceptance-suite source). All eight are settled
in [research.md](./research.md) as R-01..R-08, with R-09..R-11 recording three
further design choices the contracts depend on.

## Constitution Check

_GATE: evaluated before Phase 0, re-checked after Phase 1 design. Constitution
v1.0.0, ratified 2026-09-13._

| Principle | Pre-Phase 0 | Post-Phase 1 | Notes |
| --- | --- | --- | --- |
| I. Test-Driven Development | PASS | PASS | Every contract ends in a "Test obligations" block; `sp:05-tasks` turns them into a beads Test List. RED commits via `.venv/bin/python -m tools.commit_red`. |
| II. Type Safety | PASS | PASS | New public types (`Document`, `PositionMap`, `SymlData`, six exception classes) are fully annotated; `load`'s `IO[str] \| IO[bytes]` is checked without a cast (Contract 06). |
| III. Coverage and Lint Gates | PASS | PASS | FR-012 **removes** exemptions rather than adding them. Post-feature, the only permitted pragmas in `src/` are `if TYPE_CHECKING:` blocks. |
| IV. Spec vs Implementation Discipline | PASS | PASS | See below. |
| V. Simplicity / YAGNI | PASS | PASS | See below. |
| VI. Public API Stability | **PASS with declared breaks** | **PASS with declared breaks** | See the table below — this is FR-020. |

### Principle IV — passes now; amended as a deliverable

The gate **passes as written**: IV requires open specification questions to be
settled before implementing against them, and that is exactly what Phase 0 did —
eight items settled in research.md, none carried into implementation. IV also
requires every behaviour change to cite `todo.txt` or a D1–D17 decision; the
"Spec Conformance" section below discharges that for the feature as a whole and
every contract header carries it per-surface.

The amendment (FR-019) is a **scheduled deliverable**, not a gate waiver. It
drops two claims that become false when FR-014 and FR-016 land (that the
specification is aspirational, and that `todo.txt` is the ledger) and relaxes the
"settle before implementing" clause so the implementer may edit specification
text when implementation exposes a defect, provided the edit lands in the same
commit as the behaviour it changes.

**Version bump: 2.0.0 (MAJOR).** The constitution's own Versioning Policy
reserves MAJOR for "backward-incompatible principle removals or
**redefinitions**". Flipping a MUST clause, and removing the factual premise the
principle rests on, is a redefinition — not "materially expanded guidance"
(MINOR). Amendment Procedure steps 2, 5, and 6 (templates, propagation,
`CLAUDE.md`) are covered by FR-016 and Contract 09.

**Sequencing constraint**: the amendment must be the **first** implementation
commit. Until it lands, any commit that edits specification text alongside a
behaviour change violates IV as currently written.

### Principle V — no new runtime dependency, no second leaf type

- **No new runtime dependency.** `regex` is already declared but unused by
  `src/`; R-01 rejects starting to use it (Parsimonious compiles atoms with
  `re`, so `\p{White_Space}` would mean replacing the grammar engine). D15's set
  is enumerated inline instead. Complexity Tracking is therefore empty.
- **Every leaf value stays a plain `str`.** FR-005 strengthens this: absent
  values become `""` rather than `None`, removing the one non-string leaf that
  exists today.
- **The grammar stays line-oriented and context-free at the lexing level.** The
  two normative rules PEG cannot express — the quote-guard (R-10) and D11's
  baseline — are a line-local visitor post-check and a tree-building rule
  respectively. Neither makes lexing context-sensitive; per-line lexing (R-09)
  makes that structural rather than incidental.
- `dumps`/`dump` add a module, not a concept: §11.2 is part of the specification
  this feature exists to conform to, and FR-011 is a stated requirement.

### Principle VI — breaking changes to the semver-guarded surface (FR-020)

Principle VI requires every breaking change to `loads`/`load` signatures or to
`Source`/`Pos` semantics to bump the major version and to be listed here with
the non-breaking alternative it rejected.

| # | Breaking change | FR | Non-breaking alternative rejected, and why |
| --- | --- | --- | --- |
| 1 | **`Pos.index`, `.line`, `.column` move to original-text coordinates** — before BOM stripping and CRLF/CR normalization. A caller reading `Pos` from a CRLF or BOM-bearing document gets different numbers than in 0.6.2. | FR-013 | **Keep normalized coordinates and add an `original` field or a `to_original()` helper.** Rejected: it doubles a small, frozen value type's surface and leaves the *default* wrong for the only use case source tracking exists to serve — an editor integration placing a cursor in the file the user has on disk (§10's framing, spec US8). It also preserves a "contract" that was never documented and, because of audit gap #16, was factually wrong about line numbers anyway. |
| 2 | **`load()` widens from `TextIOBase` to `IO[str] \| IO[bytes]`**, with strict-UTF-8 decoding of binary input and a new `EncodingError` on invalid bytes. Widening a parameter type is source-compatible for callers but changes `load`'s documented contract and its failure modes. | FR-010 | **Add a separate `loadb()` for binary handles.** Rejected: §11.1 places the strict-decoding duty on `load` itself, so a second entry point would leave the existing one permanently non-conforming; and `open(path, 'rb')` handles are what callers already hold. A second function splits the installed base for no gain. |
| 3 | **Major version bump to 1.0.0**, with a clean documented break from 0.6.2 and no compatibility shim. | FR-014, FR-018 | **A 0.7 bridge release with deprecation warnings and compatibility flags.** Rejected (brainstorm Key Decisions): 1.0 is the conventional place for a break, and a bridge means writing conditional code whose only future is deletion at 1.0 — cost with no surviving value. |

**VI-adjacent changes covered by the same bump** (behaviour, not signature, but
caller-visible on the guarded surface):

- `ParseError` gains named `.message`, `.position`, `.line_text`. The existing
  positional `.args` tuple is preserved by `super().__init__(message, position,
  line_text)`, so `e.args[1]` keeps working.
- Parsimonious exceptions no longer escape `loads`/`load`; code catching
  `parsimonious.exceptions.IncompleteParseError` will stop seeing it.
- Absent values return `""` rather than `None` (FR-005) — the single largest
  behavioural break, and the one the library exists to make.

All three, plus the behaviour list above, appear in the FR-015 migration notes.

## Project Structure

### Documentation (this feature)

```text
specs/001-syml-1-0-conformance/
├── plan.md                    # this file
├── spec.md                    # the feature specification
├── research.md                # Phase 0 — R-00..R-11
├── data-model.md              # Phase 1 — entities, invariants, state machines
├── quickstart.md              # Phase 1 — orientation for the implementer
├── checklists/                # from /sp:02-specify
├── contracts/                 # Phase 1 — one file per public surface
│   ├── 01-preprocessing.md
│   ├── 02-grammar.md
│   ├── 03-tree-building.md
│   ├── 04-quoted-strings.md
│   ├── 05-errors.md
│   ├── 06-load-api.md
│   ├── 07-dump-api.md
│   ├── 08-source-tracking.md
│   └── 09-release-text.md
└── tasks.md                   # Phase 2 — created by /sp:05-tasks, NOT here
```

### Source code (repository root)

```text
src/syml/
├── __init__.py           # loads, load, parse, dumps, dump, the seven exceptions
├── preprocess.py         # NEW — §9.0, Document, PositionMap, LF-only splitting
├── parsers.py            # §4.1 grammar (transcribed), per-line SymlParser
├── nodes.py              # SymlNode tree; anchor_level/baseline/quoted on TextLeafNode
├── quoting.py            # NEW — §4.7 decode, escape table, quote-guard helpers
├── serializer.py         # NEW — §11.2 dumps/dump, quoting table, unrepresentables
├── exceptions.py         # §11.3 — seven classes with named attributes
├── basetypes.py          # Source, Pos (original-text coordinates)
└── utils.py              # line access, LF-only (str.splitlines() removed)

tests/
├── test_preprocess.py    # NEW
├── test_parsers.py
├── test_nodes.py         # currently 0 bytes; populated (FR-017)
├── test_quoting.py       # NEW
├── test_serializer.py    # NEW
├── test_exceptions.py    # NEW
├── test_basetypes.py
├── test_utils.py
├── test_spec_examples.py # NEW — extracts fenced syml blocks from the spec (R-08)
└── tools/                # unchanged

tests/acceptance/
├── conftest.py           # + the shared escaped-string fixture decoder (R-05)
└── test_us<nn>_<slug>.py # pytest-bdd bindings, marked `acceptance`

specs/acceptance-specs/
└── US<NN>-<slug>.feature # Gherkin, created by /sp:05-tasks

docs/glossary.md          # four entries refreshed, four added (Contract 09)
SYML-SPECIFICATION.md     # relabelled 1.0; §11.3, §13.4, §4.5 edits
SYML-SPEC-REVIEW.md       # subject line updated
CHANGELOG.md              # NEW (or README section) — migration notes (FR-015)
todo.txt                  # retired (FR-016)
pyproject.toml            # version = "1.0.0"
.specify/memory/constitution.md  # amended to v2.0.0 (FR-019)
```

**Structure Decision**: the existing `src/` library layout is kept unchanged.
Three new modules are added, each owning one specification section with a clean
boundary: `preprocess.py` owns §9.0 and §13.3 (nothing downstream ever sees a
`\r` or a BOM, per §4.1's opening premise); `quoting.py` owns §4.7's decode
table (pure functions, no parser state); `serializer.py` owns §11.2 (the inverse
direction, sharing nothing with the parser but the quoting table's definitions).
Splitting them out rather than growing `parsers.py` keeps each under the
100%-coverage gate with tests that name one specification section, and keeps
`parsers.py` about lexing only.

## Brainstorm Context

**Source**: [specs/brainstorms/2026-09-14-syml-1.0-spec-conformance-requirements.md](../brainstorms/2026-09-14-syml-1.0-spec-conformance-requirements.md)
and its companion audit,
[2026-09-14-syml-1.0-spec-conformance-audit.md](../brainstorms/2026-09-14-syml-1.0-spec-conformance-audit.md).

### Key decisions carried forward

- **The spec text is the 1.0 spec** — the "1.1" label recorded a review pass, not
  a language version. Relabel at release; §14's two rows fold into one.
- **Full conformance including `dumps`** — a 1.0 that cannot round-trip is a
  half-conforming 1.0.
- **Keep D17** — no new grammar for root-position quoting; `dumps` raises.
- **Clean break from 0.6.2, documented** — no bridge release, no compatibility
  flags; a bridge is code written only to be deleted at 1.0.
- **Defer all §13.4 limits** — shipping speed over resource hardening for now;
  the `RecursionError` at ~500 levels is documented as a known limitation.
- **Spec is open during implementation** — the implementer may edit spec text
  when implementation exposes a defect, edits landing in the same commit as the
  behaviour. This is why FR-019 amends constitution principle IV.
- **One feature, one epic**, despite the size.
- **Source positions in original text** — editor use is the point of source
  tracking.
- **`load()` accepts text and binary streams** — `open(path)` callers keep
  working while strict UTF-8 is enforced where bytes are available.
- **`todo.txt` is superseded** — its A1 open question is decided, A3/A4 are
  reversed on class, A9 is superseded by D11, A10 by D16, and three section-E
  "already conformant" claims are now false.

### Deferred questions, resolved during planning

All six of the brainstorm's "Deferred to Planning" items, plus the two the spec
raised in its Assumptions. Full reasoning and rejected alternatives in
[research.md](./research.md).

| Question | Resolution |
| --- | --- |
| D15's `White_Space` vs Python `\s` vs §4.1's key class — which rejects `key\x1cname: v`, and how? | **R-01**: they differ by exactly U+001C–U+001F, which `\x00-\x1f` already excludes, so the outcome is scalar fallthrough either way. The grammar enumerates D15's set explicitly (also killing the two import `SyntaxWarning`s); §4.5 gains one clarifying sentence. |
| Mechanism for mapping normalized positions back to the original | **R-02**: an offset table (`PositionMap`: BOM offset + sorted CRLF indices, `bisect_right`). `line` never needs remapping; `column` only on line 1. A CR-tolerant grammar is rejected — §4.1 explicitly assumes §9.0 has run. |
| Exact shape of `.position`, and which errors carry `line_text` | **R-03**: `.position` is always a `Pos`, `.line_text` always a `str`, both on **every** subclass, both non-optional. §11.3 states this unconditionally. Per-class anchors tabulated. |
| Fixture strategy for trailing-whitespace examples | **R-05**: every SYML fixture, acceptance and unit, is a single-line escaped string; a significant trailing space is `\x20`. Never a `"""` literal. Excluding the hook is rejected — editors strip the same whitespace (§7.5's own note). |
| Is `dumps`'s nested formatting spec-fixed or an implementation choice? | **R-06**: §11.2.1 A–G fix quoting and the one-space-after-`-`; indent width (2), blank lines (none), and trailing newline (one) are documented implementation choices, not asserted as conformance. Non-string leaves raise `TypeError`, not `UnrepresentableValueError`. |
| Does `Source`'s text-equality need changing now that duplicate keys are caught at incorporation? | **R-07**: **no change**. §10.3 *requires* text-equality and mandates incorporation-time detection precisely so it can stay. Only the `__hash__` pragma and the dead `__add__` return go. |
| `EncodingError`'s parent | **R-04**: `ParseError`, per §11.1's plain reading; §11.3 gains the entry. The real trap is that `UnicodeDecodeError.start` is a **byte** offset — position derivation is pinned in Contract 05. |
| Does the acceptance suite extract spec blocks or hand-transcribe Gherkin? | **R-08**: **both**. Gherkin per user story drives the ATDD loop; a parametrized `tests/test_spec_examples.py` extracts fenced blocks at collection time, which is the only way SC-001's "the count tracks the specification as it is edited" can hold. |

### Scope boundaries carried into the plan as explicit non-goals

- §13.4's implementation limits (depth, line length, document size) and
  `DocumentLimitError`. The seven exported classes are the complete 1.0 list.
- Any v1.2 syntax: `[]`/`{}` empty-collection tokens, quoted keys,
  surrogate-pair combining, an error for a tab after a structural marker.
- Root-scalar quoting (D17).
- A deprecation or bridge release, and any compatibility flags.
- Publishing to PyPI — no tag, no build, no upload (FR-018, US9.9).

## Spec Conformance

_Required by constitution principle IV: every behaviour change cites a `todo.txt`
entry or a D1–D17 decision record._

This feature does not close "a" gap — it closes **all twenty-one** of the audit's
verified gaps except #15, which is deferred by decision. Mapping:

| Audit gap | Closed by | `todo.txt` | Decision record |
| --- | --- | --- | --- |
| 1. Quoted strings absent | FR-008 / Contract 04 | A1 (its OPEN QUESTION **decided** — do not re-litigate) | D2, D3, D4 |
| 2. Quoting inline-only; inline non-quote fallthrough raises | FR-008 / Contract 04 | A1 (scope narrowed) | D2, M19 |
| 3. Sibling acceptance `>=` not `==`; closed nodes absorb | FR-006 / Contract 03 | A4 (**reversed on class** — D7, no `InconsistentIndentationError`; and understated the fix) | B4, D7 |
| 4. No continuation baseline; indentation flattened | FR-006 / Contract 03 | A9 (**superseded** by D11) | D11, B5 |
| 5. Plain text at a container's level joins | FR-006 / Contract 03 | section E stale | M24 |
| 6. Empty values yield `None` | FR-005 / Contract 03 | A2 (extended by D6) | D6 |
| 7. Bare `-` unsupported; `key:value` errors | FR-004 / Contract 02 | A10 (**superseded** by D16) | D16, §7.6 |
| 8. No §9.0 pre-processing | FR-002 / Contract 01 | A3 (**reversed on class** — `TabIndentationError`), A7, A8 | D14, D5 |
| 9. Tab accepted as separator whitespace | FR-004 / Contract 02 | section E stale (§7.5) | D5 |
| 10. No duplicate-key detection | FR-007 / Contract 03 | A6 | B6, M16, §10.3 |
| 11. Error taxonomy is 2 of 7 classes | FR-009 / Contract 05 | B2 | §11.3, D7 |
| 12. Parsimonious exceptions leak | FR-009 / Contract 05 | B2 | B2, R-09 |
| 13. `indent = ~"\s*"` swallows whitespace-only lines | FR-004 / Contract 02 | B1 | B1, §4.4 |
| 14. Inline key after `-` does not set the sibling column | FR-006 / Contract 02, 03 | — | M23, §6.2, R-11 |
| **15. No implementation limits; deep nesting crashes** | **DEFERRED** — documented known limitation | — | D10 (limits are SHOULD); brainstorm Key Decisions |
| 16. Positions miscount lines around U+2028 | FR-003, FR-013 / Contract 01, 08 | — | M12, §13.3 |
| 17. No `dumps`/`dump` | FR-011 / Contract 07 | — | D1, D8, D17, §11.2 |
| 18. `load()` decode policy | FR-010 / Contract 06 | — | M13, §11.1 |
| 19. Hygiene: empty `test_nodes.py`; `as_source` pragma blanket | FR-012, FR-017 / Contract 08 | — | — |
| 20. Hygiene: two import `SyntaxWarning`s | FR-017 / Contract 02 | — | R-01 (fixed by D15's enumerated class) |
| 21. Hygiene: `pyproject.toml` says 0.6.2 | FR-014 / Contract 09 | m6 (`tox.ini`) already done | — |

**Open specification questions settled before Phase 1 finished** (principle IV's
second clause): all eight, in research.md R-01..R-08. The only one requiring a
normative specification edit is `EncodingError`'s addition to §11.3 (R-04);
R-01's §4.5 edit is clarifying only. Contract 09 lists the complete set of spec
edits this feature makes.

## Applied Learnings

`.specify/solutions/` exists but holds only `INDEX.md` with no entries yet
(`_(none yet)_`). The category directories relevant to this feature —
`parsing/`, `spec-conformance/`, `python-typing/`, `pytest-coverage/`,
`security/`, `tooling/` — are declared but empty. **No prior learnings apply.**

Candidates this feature is likely to generate, for the `/compound` skill at
`sp:08-harden`: Parsimonious's evaluation of `~"..."` bodies as Python string
literals (`parsing/`); the byte-vs-code-point trap in `UnicodeDecodeError.start`
(`python-typing/` or `parsing/`); the `trailing-whitespace` hook versus SYML
fixtures (`tooling/`).

## Acceptance Test Strategy

> **ATDD outer loop**: each user story with acceptance scenarios gets a
> `.feature` file created during `sp:05-tasks`. Ralph's ATDD cycle depends on
> these existing before `US<N>` tasks are processed.

| User Story | Acceptance Spec File | Bindings | Scenarios |
| --- | --- | --- | --- |
| US1: Tree building follows §9.3 | `specs/acceptance-specs/US01-tree-building-acceptance.feature` | `tests/acceptance/test_us01_tree_building_acceptance.py` | 10 |
| US2: Pre-processing per §9.0/§13.3 | `specs/acceptance-specs/US02-preprocessing.feature` | `tests/acceptance/test_us02_preprocessing.py` | 7 |
| US3: Lines lex per the §4.1 grammar | `specs/acceptance-specs/US03-line-lexing.feature` | `tests/acceptance/test_us03_line_lexing.py` | 9 |
| US4: Absent values are `""` | `specs/acceptance-specs/US04-empty-values.feature` | `tests/acceptance/test_us04_empty_values.py` | 5 |
| US5: Error taxonomy and entry API | `specs/acceptance-specs/US05-error-taxonomy.feature` | `tests/acceptance/test_us05_error_taxonomy.py` | 6 |
| US6: Quoted strings per §4.7 | `specs/acceptance-specs/US06-quoted-strings.feature` | `tests/acceptance/test_us06_quoted_strings.py` | 10 |
| US7: Round-trip `dumps`/`dump` | `specs/acceptance-specs/US07-serialization.feature` | `tests/acceptance/test_us07_serialization.py` | 9 |
| US8: Source tracking, original-text positions | `specs/acceptance-specs/US08-source-tracking.feature` | `tests/acceptance/test_us08_source_tracking.py` | 5 |
| US9: Release-ready `main` | `specs/acceptance-specs/US09-release-readiness.feature` | `tests/acceptance/test_us09_release_readiness.py` | 9 |
| | | **Total** | **70** |

**Pipeline**: pytest-bdd via `just acceptance`. Gherkin lives in
`specs/acceptance-specs/`, bindings in `tests/acceptance/`, marked `acceptance`;
the unit run both deselects that marker and `--ignore`s the directory.

**Three strategy notes for `sp:05-tasks`:**

1. **Fixture encoding (R-05).** Every SYML document in a `.feature` file is a
   single-line double-quoted string using escapes (`\n`, `\t`, `\r`, `\x20`,
   `﻿`, ` `). A shared step in `tests/acceptance/conftest.py` decodes
   it with an explicit, audited unescape table — **not** `codecs.decode(...,
   'unicode_escape')`, which round-trips through latin-1 and mangles the
   non-ASCII content US2/US3/US8 fixtures require. No triple-quoted docstring
   arguments anywhere.
2. **US7 scenario 1 is a property, not an example.** `loads(dumps(x)) == x` over
   a representable corpus: write it as a `Scenario Outline` over a shared corpus
   fixture (Contract 07 lists what the corpus must contain), not as one row.
3. **US9's nine scenarios are repository-inspection steps**, not parser tests —
   they bind against file contents, `importlib.metadata.version('syml')`, and
   `git tag --list`. They belong in the acceptance suite, where a non-parser
   Given/When/Then reads naturally, rather than in the unit run.

**Separately from the ATDD loop** (R-08): `tests/test_spec_examples.py` runs in
the ordinary unit suite and parametrizes every fenced ` ```syml ` block in
`SYML-SPECIFICATION.md` that states an `**Output:**`, at collection time. This
is what satisfies SC-001's clause that "the count tracks the specification as it
is edited" — a hand-transcribed suite silently stops covering a block the moment
someone edits the spec, which FR-019's amendment makes likely. It asserts a
minimum block count (53) so a regex-drift bug fails loudly rather than passing
vacuously. It lives under `tests/` (inside the mypy file set, outside the
coverage gate), not `tools/` and not `src/`.

## Complexity Tracking

> Fill only if the Constitution Check has violations that must be justified.

**Empty.** The Constitution Check records three declared breaking changes under
principle VI (which VI *provides for*, given a major bump and a listed rejected
alternative — all three are supplied), not violations. No new runtime
dependency, no second leaf type, no context-sensitivity at the lexing level, no
coverage exemption added — FR-012 removes exemptions.

One note, recorded rather than justified: if `sp:05-tasks` or `sp:07-implement`
concludes that US7's round-trip property (SC-003) needs `hypothesis`, it would
be a **dev-group** dependency, not a runtime one. Principle V governs runtime
dependencies; a test-only addition does not trigger it. The plan's default is a
hand-curated corpus (Contract 07), which is sufficient for SC-003 as written.

## Phase status

| Phase | Status | Output |
| --- | --- | --- |
| 0.4 Brainstorm context | complete | § "Brainstorm Context" above |
| 0.5 Prior learnings | complete | § "Applied Learnings" — none exist |
| 0 Research | complete | [research.md](./research.md) — R-00..R-11, zero unresolved |
| 1 Design & contracts | complete | [data-model.md](./data-model.md), [contracts/](./contracts/) ×9, [quickstart.md](./quickstart.md) |
| Constitution re-check | complete | table above; PASS with three declared VI breaks |
| 2 Tasks | **not started** | `/sp:05-tasks` — this command stops here |

**Next**: `/sp:04-red-team`. Two items from research.md are flagged for
adversarial attention: R-09's claim that a per-line `IncompleteParseError` can
only mean trailing-content-after-quote, and R-02's claim that `line` never needs
remapping (boundary cases: a document ending in a bare `\r`, and `\r\r\n`).
