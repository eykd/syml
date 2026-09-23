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
decision. Nesting past ~500 levels of block nesting — or only ~120 levels of
inline `- - - …` nesting on one line, which recurses during lexing — raises the
host `RecursionError` and is
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
direction, sharing nothing with the parser but the quoting table's definitions
and a read-only use of `GRAMMAR['line']` to re-lex list-item renderings —
Contract 07's one exception to the single-quote preference).
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
  the `RecursionError` (~500 block levels, ~120 inline levels on one line) is
  documented as a known limitation.
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
| Mechanism for mapping normalized positions back to the original | **R-02**: an offset table (`PositionMap`: BOM offset + sorted CRLF indices, `bisect_left` — corrected from `bisect_right` by red team, see § Edge Cases & Error Handling). `line` never needs remapping; `column` only on line 1. A CR-tolerant grammar is rejected — §4.1 explicitly assumes §9.0 has run. |
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
   arguments anywhere. The decoder **raises** on any backslash sequence not in
   its table, so a mangled fixture fails loudly instead of loading as something
   else. **SYML text never goes in an `Examples:` table cell**: gherkin-official
   (29.0.0, pinned via pytest-bdd 8.1.0) unescapes cells before pytest-bdd
   substitutes them — `\\` becomes `\`, `\n` a real newline, `\|` a `|` — while
   inline step text arrives raw (verified with the installed parser). A cell
   `a\\: b` would reach the decoder as `a\: b`: double-decoded or rejected.
   Fixtures live only in inline step strings, decoded exactly once.
2. **US7 scenario 1 is a property, not an example.** `loads(dumps(x)) == x` over
   a representable corpus: write it as a `Scenario Outline` whose `Examples:`
   rows carry **corpus identifiers** that index a shared Python corpus fixture
   (Contract 07 lists what the corpus must contain), not the strings themselves
   and not one row. Pass 4 added backslash-bearing entries (`a\: b`,
   `a: 'b" \c`) that note 1's cell hazard would corrupt.
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

## Edge Cases & Error Handling

_Added by `/sp:04-red-team`, pass 1 (2026-09-23). Each item below was verified
against the transcribed §4.1 grammar under the pinned Parsimonious, not argued
from reading. None changes a D1–D17 decision._

### Position mapping at collapsed CRLF breaks (Contract 01, 08; data-model §1a)

- **`to_original` uses `bisect_left`, not `bisect_right`.** The only
  normalized positions that land *on* a collapsed-break index are the exclusive
  `end` of every token that ends a CRLF-terminated line, and empty tokens at
  end of line (`k:␠`). Both mean "end of this line's content", which is the
  `\r` in the original. `bisect_right` mapped them to the `\n`: for value `b`
  in `"a: b\r\nc: d"`, `original[start.index:end.index]` was `"b\r"` and the
  `end` `Pos` had an `index` disagreeing with its own `column`. That is every
  value on every CRLF line. A brute-force consistency check (97,855 positions)
  found `bisect_right` wrong at 18,654 — exactly the `crlf_indices` positions —
  and `bisect_left` right everywhere.
- This **reverses the deepen-plan conclusion** recorded in research.md's open
  item 2: its round-trip checked each index against the plan's own convention,
  so it could not see that the convention was inverted. The `line` claim
  (never remapped) and the `\r\r\n` / trailing-bare-`\r` cases do hold.
- Test obligation added: a span property,
  `original[start.index:end.index] == source.text`, over CRLF/CR/BOM corpora,
  and a reference check over **every** normalized index including the
  collapsed-break ones.

### Anchoring trailing-content errors at the opening quote (Contract 02, 05)

- `IncompleteParseError.pos` is the strand point; the error must anchor at the
  opening quote. The entry point therefore calls `GRAMMAR['line'].match()` and
  treats `pnode.end < len(line.text)` as the §4.7 trailing-content case. The
  prefix tree always holds exactly one `quoted_value`; its `.start` is the
  anchor. No `IncompleteParseError` is caught, and no unreachable "unknown
  parse failure" branch exists.
- Precedence is pinned: stranding is detected before visiting, so
  `k: "\ud800" x` reports trailing content (`escape=None`), not the surrogate.

### Diagnosing the quote-guard fallthrough (Contract 04)

- An invalid or incomplete escape (`\x`, `\u12`) makes `double_quoted` fail
  to match, so the value falls through to `data` and reaches the quote-guard,
  never `decode_double_quoted`. As first contracted, nothing could populate
  `.escape="\\x"` for Contract 04's own table row.
- `quoting.diagnose_malformed(text) -> str | None` scans left to right; the
  first invalid/incomplete escape wins, otherwise the value is unterminated.
  Surrogates and code points above U+10FFFF still match the grammar and are
  reported by the decoder, so the two paths partition the malformed cases.

### `data` is not a node (Contract 02)

- `data = text` is an alias: Parsimonious resolves both names to one expression
  named `text`, so `visit_data` never fires and comment bodies share the same
  expression. The quote-guard lives in `visit_key_value` / `visit_list_item`.

### Exceptions escaping through the visitor (Contract 05)

- Parsimonious wraps any non-`unwrapped_exceptions` error raised in a
  `visit_*` method as `VisitationError`, a Parsimonious class (FR-009).
  `unwrapped_exceptions = (ParseError, RecursionError)`, and tree incorporation
  runs outside `NodeVisitor.visit`.
- **Inline nesting hits `RecursionError` far earlier than block nesting**: a
  single line `'- ' * 123 + 'x'` (~250 bytes) exhausts CPython's default limit
  inside Parsimonious's lexing. The §13.4 deferral stands (brainstorm Key
  Decisions — an intentional exclusion, not reopened); only the documented
  figure changes: Contract 09's known-limitation note states both depths.
- **Strings do not inherit the limitation in the dump direction.** `dumps`
  lexes candidate strings for rule D and §11.2.4(a); a `RecursionError` from
  that probe means "matches `structure`" (pass 4 below, Contract 07). Deeply
  nested *data* is still subject to the deferred depth limit in `dumps`.

### `line_text` (Contract 05)

- `line_text` is the **original** physical line without its terminator,
  keeping a leading BOM on line 1, so `line_text[position.column]` is the
  anchor character on LF, CRLF, and BOM documents alike. Taking the normalized
  line would be off by one on a BOM-bearing line 1.

### Pass 2 (2026-09-23): second-order checks

- **No-space quoted values escape the quote-guard (§4.1 as printed).**
  `k:"abc` and `k:"a\xb"` match neither `key_value` alternative (the
  second needs `ws`) nor `section`, so the line is root-level `data` and parses
  as a scalar with no error; `k:"ab"` is a mapping. Contract 04 pins these rows
  as tests of the grammar as printed and raises the question below.
- `TabIndentationError` is found on normalized text; its position goes through
  `to_original`, so a BOM-bearing line 1 reports the tab at column 1
  (Contract 01 row added).
- `diagnose_malformed` reads `''` exactly as the grammar does, so `k: 'a''` is
  unterminated (Contract 04).
- Re-checked with `bisect_left`: empty tokens at a CRLF line end and the
  BOM-plus-line-1 column rule stay consistent (covered by the 97,855-position
  brute force, which includes both).

### Pass 3 (2026-09-23, outer iteration 2): quoted list items that lex as mappings

- **`key`'s class admits `'` and `"`, and `value` tries `structure` before
  `quoted_value`.** So a *well-formed* quoted list item whose content begins
  with key characters followed by `: ` re-lexes as a mapping: `- 'a: b'` is
  `[{"'a": "b'"}]` and `- "a: b"` is `[{'"a': 'b"'}]`, both with no error.
  Verified against the transcribed grammar. The mapping side is clean —
  `k: 'a: b'` is `{"k": "a: b"}`, because `key_value`'s first alternative tries
  `quoted_value` before anything else — so §11.2.1 rule D's mapping exemption
  holds and only list items are affected.
- **Consequence for `dumps` (High).** Rule D forces quoting of the list-item
  string `a: b`, and the single-quote preference renders it `- 'a: b'`, which
  `loads` reads back as a mapping. `loads(dumps(["a: b"])) == [{"'a": "b'"}]`:
  silent corruption, and Contract 07's own corpus (`key: v`-shaped strings)
  would fail SC-003's property at implementation time. Brute force over every
  string up to length 6 on `ab:' "-#/\x`: 112,230 single-quoted and 65,453
  double-quoted list-item renderings re-lex as something other than one
  `quoted_value`. **Mitigation (Contract 07)**: at a list-item inline position,
  when the chosen quoted rendering re-lexes as anything but
  `list_item > quoted_value` spanning the line, `dumps` emits the
  double-quoted form with every `:` written `\u003a`. With no literal `:`,
  `key_colon` cannot match and the line can only lex as a quoted value
  (0 failures in the same brute force). §11.2.1's single-quote rule is a
  preference, not a MUST, and its `loads(dumps(x)) == x` requirement is a MUST,
  so this is conformant and needs no spec edit.
- **Consequence for the quote-guard (second-order to pass 1's relocation).**
  An *unterminated* quote in the same shape — `- 'a: b` or `- "a: b` — is also
  intercepted by `structure` and becomes `[{"'a": "b"}]` with no error. Pass 1
  put the guard in `visit_key_value` / `visit_list_item`, which is correct, but
  the grammar routes these lines around it: the list item's value is a
  `key_value` whose `data` is `b`, not a quote-led `data`. The guard cannot see
  them from any visitor. Pinned as tests of the grammar as printed
  (Contracts 02, 04); the fix is a grammar edit, so it is open item 4 below.
- **Iteration 1's mitigations re-probed and held**: the "exactly one
  `quoted_value` in a stranded prefix" claim on `- k: "a" x`, `- - "a" x`,
  `"a": "b" x` (where the quote-led key `"a"` is a `key`, not a
  `quoted_value`), `k: "a"　`, and `k: "a"\x0c`; `bisect_left` on the
  `\r\r\n` and trailing-bare-`\r` boundaries; and `RecursionError` in
  `unwrapped_exceptions` (Parsimonious's `visit` catches `Exception`, of which
  `RecursionError` is a subclass, so the tuple entry is required, not
  redundant).
- **`load(open(p))` positions are in newline-translated text (Contract 06).**
  A text handle opened with the default `newline=None` has already turned
  `\r\n` and `\r` into `\n` before `load` sees it, so `Pos.index` on a CRLF
  file is not the on-disk offset FR-013 promises — `line` and `column` still
  agree. `load` cannot undo the translation. Documented in `load`'s docstring
  and the migration notes: for editor-grade positions pass a binary handle or
  `open(p, newline='')`. Pinned as a test.

### Pass 4 (2026-09-23, outer iteration 3): the serializer's grammar probes

Probed against the transcribed grammar with a reference renderer: every string
up to length 5 on `ab:'" -#/\` plus TAB (177,156 strings) round-trips at the
list-item position under pass 3's fallback (4,399 take the `:` form), and
every one round-trips at the mapping-value position with no fallback. Both
quote kinds plus colons, leading/trailing space or tab, leading `#`/`//`, and
the empty string as bare `-` (Contract 03: `-` with no child is `""`) all hold.
The brute force implemented the *intended* reading of Contract 07's steps; the
findings below are where the written contract departs from it.

- **`dumps` raises the host `RecursionError` on a representable value (High).**
  Rule D ("would itself match `list_item`, `key_value`, or `section`") and
  §11.2.4(a) are decided by lexing the raw string, and `structure` recurses in
  Parsimonious once per inline `- `. `GRAMMAR['structure'].match('- ' * 150 +
  'x')` raises `RecursionError` (100 levels pass). But the value *is*
  representable: `- '- - … x'` loads fine, because a quote-led line fails
  `structure` at its first character and the `*` repetitions inside
  `single_quoted`/`double_quoted` are iterative (verified at 300 levels, both
  quote kinds). So `dumps(['- ' * 150 + 'x'])` crashes on a ~300-byte string
  that §11.2.1 requires it to serialize — a violation of the round-trip MUST,
  not an instance of the deferred §13.4 limits. **Mitigation (Contract 07)**:
  the rule-D / §11.2.4(a) probe catches `RecursionError` and treats it as
  "matches `structure`" — a string whose lexing recurses that deep begins with
  `- ` and is a list item by construction. At a list-item position that
  means "quote it" (the quoted re-lex is shallow; a mapping value is exempt
  from rule D and is never probed); at the root it means
  `UnrepresentableValueError`. The probe never lets `RecursionError` escape;
  `dumps`'s own walk over deeply nested *data* (~1,000 levels) is the deferred
  §13.4 limit in the dump direction, stated as such in Contract 09 (second
  pass of this iteration). A probe that trips only because the stack is
  already deep over-quotes a list item — safe, since quoting never breaks the
  round-trip.
- **Rule D's probe must accept a stranded prefix (Medium).** `k: "a" x` fails
  `GRAMMAR['structure'].parse` (`IncompleteParseError`) but `match` returns the
  prefix `k: "a" `. An implementation that asks "does the whole string parse as
  structure" leaves it unquoted, emits `- k: "a" x`, and `loads` then raises
  `MalformedQuotedStringError` (trailing content) on its own output. **Rule D
  is decided by `match` (prefix), not `parse`**: any structure match, stranded
  or not, requires quoting. Same for `k: 'v' x` and §11.2.4(a).
- **Contract 07's steps 1–2 read literally force-quote every list item
  (Medium, Congruence).** Pass 3 above scoped the re-lex to "the chosen quoted
  rendering"; Contract 07's step 1 applied it after rules A–F unconditionally,
  so a plain `hello` (re-lexes as `list_item > text`, not `quoted_value`) would
  become `- "hello"` and the empty string `- ""` — the latter breaching rule A's
  "never `''` or `""`". Contract 07 now runs the re-lex only when a rule
  required quoting; its test obligation already allowed the unquoted `text`
  outcome.
- **The fallback's escaping is single-pass, and the corpus lacked a backslash
  (Medium).** The `:` fallback composes with `\\` and `\"` escaping only if
  every character is escaped in one pass. Substituting `:` first and escaping
  `\` second turns the inserted `:` into `\\u003a`, which loads as the
  literal text `:` — silent corruption. Contract 07's corpus had no
  backslash, so that ordering bug would pass SC-003. Added to the corpus:
  `a\: b`, `:` as literal text, and `a: 'b" \c` — each as a list item.

### Pass 5 (2026-09-23, outer iteration 4): load API, source tracking, release text

Aimed at the surfaces iterations 1–3 had not attacked. No Critical or High
finding. R-09's stranded-prefix claim and the `\r\r\n` / trailing-bare-`\r`
boundaries were not reopened by anything below.

- **Quoted-value spans contradicted the span property (Medium, Congruence).**
  data-model §4 makes a quoted value's `Source.text` the decoded string;
  Contract 08's property asserted `original[start:end] == text` for every
  single-line node, which no quoted value with quotes or escapes can meet.
  Contract 08 now pins the span as opening quote to past the closing quote
  (the `MalformedQuotedStringError` anchor), and the property decodes the raw
  slice for quoted nodes rather than excluding them.
- **Gherkin `Examples:` cells are pre-unescaped (Medium).** See Acceptance Test
  Strategy notes 1–2: SYML text stays out of table cells; US7's outline rows
  name corpus entries.
- **A text handle over invalid UTF-8 leaked `UnicodeDecodeError` (Medium).**
  `read()` decodes, so the error escaped `load` before its bytes branch —
  against FR-009. Contract 06 wraps `read()` and raises `EncodingError`; R-04's
  derivation applies to `(err.object, err.start)`, verified on a real file. The
  no-U+FFFD invariant is scoped to bytes `load` decodes itself.
- **US9.1 and US9.9 go false at release (Medium).** CI runs `just acceptance`
  on every push, tag pushes included, with tags fetched. Contract 09 tags both
  `@feature-exit` and makes their removal the first step of the manual release.
- **`file_obj.name` can be an int (Low).** `TemporaryFile().name` is a file
  descriptor; Contract 06 accepts only `str` / `os.PathLike`.
- **Contract 09 congruence (Low).** The migration notes gain the text-handle
  position caveat and `parse`'s promotion; the amended citation duty names the
  B/M records plan.md already cites; the first commit does not make
  `CLAUDE.md` claim conformance ahead of FR-016.

### Pass 6 (2026-09-23, outer iteration 5): congruence sweep

No Critical or High finding; a red-team congruence check across plan.md,
data-model.md, and contracts 04/05/06/08/09, per the orchestrator's targets.
R-09's stranded-prefix claim and the `\r\r\n` / trailing-bare-`\r` boundaries
were re-checked and not reopened.

- **Quoted-value span wording disagreed (Low).** data-model §4 said the span
  ran "from opening to closing quote", readable as `end` landing *on* the
  closing quote; Contract 08 already said "just past the closing quote
  (exclusive)". data-model §4 now matches Contract 08 word for word.
- **Contract 08's span property called an undefined `decode()` (Low).**
  Contract 04 exports `decode_single_quoted`/`decode_double_quoted`, no
  generic `decode`. Contract 08's test obligation now dispatches on the
  slice's leading quote character to the two named decoders; Contract 04's
  docstrings now say each takes the full grammar match, quotes included, so
  the slice Contract 08 decodes is exactly what the decoders expect.
- **Contract 05's `EncodingError` derivation used a bare `raw` (Low).**
  Contract 06 cites the derivation as being over `(err.object, err.start)`;
  Contract 05 now uses `err.object` by name and states the derivation holds
  regardless of whether the bytes came from a binary handle or a text
  handle's internal `read()`.
- **`@feature-exit`'s runtime semantics were unstated (Medium).** Contract 09
  named the tag and the pyproject registration but not what `just acceptance`
  does with it. Verified against the pinned pytest-bdd 8.1.0 (scratch
  collection): a Gherkin `@tag` becomes a pytest marker under the **literal**
  string, hyphen included (`feature-exit`, not `feature_exit`); both
  scenarios run normally, with no deselection, on every invocation up to and
  including the commit that removes them (FR-018); that removal is the only
  mechanism keeping release CI green. Noted as distinct from the project's
  own `acceptance` marker (applied by hand as a module-level `pytestmark`,
  per the acceptance-tests skill), which cannot target 2 of 9 scenarios in
  one `.feature` file.
- **Contract 04's round-trip test obligation called an undefined
  `dumps_quoted` helper (Low), same defect class as the `decode()` gap
  above.** Contract 07 exports only `dumps`/`dump`, no single-value quoting
  helper. Rewritten as `loads(dumps({'k': s}))['k'] == s`, using the actual
  public surface.

### Pass 7 (2026-09-23, outer iteration 5): per-line plumbing

A cross-contract API sweep: every helper a contract calls, checked for a
definition with a matching signature. The R-09 stranded-prefix claim and the
`\r\r\n` / trailing-bare-`\r` boundaries were re-checked and still hold; the
iteration-5 edits opened nothing. Three problems, all in how Contract 02's
per-line loop connects to the rest. Each was verified against Parsimonious.

- **Tab-bearing blank lines were never dropped (High).** D14 says a blank line
  is "discarded before any other check". Contract 01 only skipped the *tab
  check*, and Contract 02's loop had no skip at all. Its delta row said "a
  blank line is a `data` match of `""`", which is false once a tab is
  involved. `"  \t  "` lexes as `indent` `"  "` plus a **non-empty** `data`
  `"\t  "` (verified), so `"  \t  \nkey: v"` (US2.6's shape, SC-002's
  "tab-only line" probe) would make `"\t  "` the root scalar and then raise
  `OutOfContextNodeError`. And `"key: a\n  \t\n  b"` would absorb a `"\t"`
  continuation, which breaks D12. A `preprocess`-only unit test passes either
  way. **Mitigation**: one `is_blank(text)` predicate in `preprocess.py`,
  shared by the tab scan and the loop, which `continue`s before `match`.
  Pinned through `loads` in Contracts 01 and 02. This transcribes D14; it does
  not change it.
- **Positions had no defined path from a line-local `pnode` (High).** Per-line
  `match` makes `pnode.full_text` the **line** (verified). Today's
  `Source.from_node(pnode, filename)` computes `line`/`column` with
  `Pos.from_str_index(pnode.full_text, …)`, so it would report line 1 for
  every node and use line-local indices. Contract 08 said only that
  `from_node` "takes the `PositionMap`". Contract 02 called
  `visitor.visit(pnode, line)`, but `NodeVisitor.visit` takes one argument
  (verified `TypeError`). Contract 05's `raise_trailing_content` used an
  undefined `pos_at` and an out-of-scope `doc`. These are the same defect
  class as pass 6's `decode()`/`dumps_quoted`, but load-bearing.
  **Mitigation**: `pos_at(line, offset) -> Pos` in Contract 01;
  `Source.from_node(pnode, line, position_map, filename)` in Contract 08; the
  visitor is built once per `Document` and the loop sets `visitor.line`;
  `raise_trailing_content(pnode, line, doc)` with an `original_line` helper.
  `Pos.from_str_index` and `Source.from_text` stay (the existing tests use
  them) but count `\n` only and are never used for parse positions.
- **`decode_double_quoted` could not raise the error it promised (Medium).**
  It is position-free, and `MalformedQuotedStringError.position` is never
  `None`. A private exception leaving a `visit_*` method would be wrapped in
  `VisitationError` (verified). **Mitigation**: the decoder raises a private
  `QuotedStringDefect`, which the calling `visit_key_value`/`visit_list_item`
  converts **within the same method** (Contracts 04, 05). The subclass
  constructors now take their extra attributes keyword-only
  (`*, escape, code_point` / `*, key, first_position`), so `.args` stays three
  elements. data-model §5's stale `contracts/errors.md` link now points at
  `05-errors.md`.

### Pass 8 (2026-09-23, outer iteration 6): the rest of the per-line plumbing sweep

Pass 7 fixed the load-bearing helpers but left two classes of the same defect
uncaught. The R-09 stranded-prefix claim and the `\r\r\n` / trailing-bare-`\r`
boundaries were re-checked once more and still hold; nothing below touches
them.

- **`original_line` and `find_first` were called, never defined (High).**
  Contract 05's `raise_trailing_content` called both; neither had a `def`
  anywhere, and `find_first` is not a parsimonious `Node` method (verified:
  `Node`'s public surface is `children, end, expr, expr_name, full_text,
  prettily, start, text`). **Mitigation**: both defined in Contract 05,
  immediately above `raise_trailing_content`, with `original_line`'s
  docstring pinned to the same single-pass `\r\n|\r|\n` regex split Contract
  01 uses for normalization — never `str.splitlines()` (§13.3).
- **`incorporate_node`'s failure path had no way to build `line_text` (High).**
  Contract 02's loop called a module-level `incorporate(tip, node)` that
  Contract 03 never defined; Contract 03 defined a same-named *method*,
  `SymlNode.incorporate_node(self, node)`, with no `doc` parameter. Today's
  `fail_to_incorporate_node` builds its position from `pnode.full_text` via
  `Pos.from_str_index`, which is exactly the "line 1 for every node" defect
  pass 7 fixed on the visitor side (Contract 08) — untouched here, because
  `fail_to_incorporate_node` doesn't go through the visitor at all. And
  `Mapping.can_add_node`'s duplicate-key raise (§10.3) needs the same
  `line_text` with no `doc` in scope either. **Mitigation**: `doc: Document`
  added as a required second argument to `incorporate_node` and
  `can_add_node`, threaded unchanged through every recursive call; position
  comes from the node's own `Source.start` (already original coordinates,
  Contract 08) and `line_text` from Contract 05's new `original_line(doc,
  position.line)`. Contract 02's call site becomes
  `tip.incorporate_node(node, doc)`. `KeyValue.key` is a `KeyLeafNode`, not a
  string, so the duplicate-key comparison and the `DuplicateKeyError.key: str`
  attribute both go through the existing `.as_data()` conversion
  `Mapping.as_data`/`as_source` already use, rather than comparing nodes or
  inventing a second string accessor.
- **`SymlParser`'s constructor signature changed without a surface note
  (Low).** Today's `SymlParser(filename: StrPath | None = None)` becomes
  `SymlParser(doc: Document)` under per-line lexing (pass 7's `visitor.line`
  mechanism needs `position_map` too), but no contract said so plainly.
  **Mitigation**: one sentence in Contract 02 stating the before/after and
  that `filename` is still reachable as `doc.filename`.

### Pass 9 (2026-09-23, outer iteration 7): tree-building sweep after `doc` threading

R-09's stranded-prefix claim and the `\r\r\n` / trailing-bare-`\r` line
boundaries still hold. `\r\r\n` is two breaks both before and after
normalization, and a trailing `\r` is one. Nothing below touches them.

- **`Mapping.can_add_node` ran the duplicate scan before the level test
  (High).** Contract 03's code checked every incoming `KeyValue` against the
  mapping's keys first, while its own prose, spec §9.3's table, and
  data-model §3.2 all scope the check to `node.level == mapping.level`.
  `p:\n  a: 1\na: 2` walks up through the level-2 mapping holding `a` before
  it reaches the root mapping, so the code raised `DuplicateKeyError` on a
  valid document (§8.3: "the same key may appear in different nested
  mappings"). **Mitigation**: the code now tests the level gate first and
  returns `False` without scanning on a mismatch. The input is now a worked
  case and a test obligation. This is a transcription fix, not a decision
  change.
- **The per-line loop dropped comment routing (High).** Contract 02's loop
  passed every visited node to `incorporate_node`. `Comment` is a
  `TextLeafNode` subclass, so a comment inside a value would have joined as
  continuation text (breaking D12), and `"# only"` would have become a root
  scalar. data-model §2 and today's `visit_lines` both attach comments to
  `tip.comments`. **Mitigation**: the loop gets an explicit `Comment` branch
  before `incorporate_node`. Both cases are test obligations in Contract 03.
- **`Root` and auto-created intermediaries had no way to build a `Source`
  (Medium).** `__post_init__` derives `source` from `Source.from_node`,
  which now needs a `line`. `incorporate_node` has no `line`, and under
  per-line lexing `Root` has no document-level `pnode`. The loop also never
  initialized `tip`. **Mitigation**: `source` is a constructor field built
  by the visitor. Intermediaries copy the triggering node's `Source`. `Root`
  is `pnode=None` with an empty `Source` at `Pos(0, 1, 0)`, which is the
  "empty span" data-model §3.5 promised. The loop constructs `root = tip`
  and returns `root` (Contracts 02 and 03, data-model §3.4).
- **Contract 05 said all incorporation runs outside `NodeVisitor.visit`
  (Low).** Inline structure (`- key: v`) incorporates inside
  `visit_key_value`/`visit_list_item`, which §9.2 requires. It is safe
  because only `ParseError`/`RecursionError` can escape, and both are
  unwrapped. The rule now says that, and those calls pass `self.doc`.

### Open items for the principal (not applied)

1. **Widen `escape_seq` to `'\\' ~"."`** so the decoder validates every escape
   in one place and `diagnose_malformed` disappears. Simpler, but it departs
   from §4.1's grammar as printed; recorded, not adopted.
2. **spec.md's Edge Cases bullet** says documents nested "past roughly 500
   levels" raise `RecursionError`. True for block nesting; inline nesting on
   one line fails at ~120. The red team did not edit spec.md; the release text
   (Contract 09) carries both figures.
3. **Should the quote-guard also fire on `key:` immediately followed by a
   quote?** Today `key:"value"` is a mapping but `key:"unterminated` is a
   silent scalar. Extending the guard is a normative §4.1 edit bearing on D2's
   intent, so it is left for the principal; the plan implements and tests the
   grammar as printed.
4. **Should a quote-led list item ever lex as a mapping?** Under §4.1 as
   printed, `- 'a: b'` is `[{"'a": "b'"}]` and `- 'a: b` is `[{"'a": "b"}]`
   with no error (pass 3 above). `dumps` works around it (Contract 07); a
   hand-author does not get the same protection. Two grammar edits were run
   against the transcribed grammar, neither applied:
   (i) reorder to `value = (quoted_value ~" *") / structure / data` — fixes the
   terminated case, but `- 'a: b` (unterminated) still lexes as a mapping;
   (ii) add `'` and `"` to `key`'s excluded class — fixes both (the
   unterminated case reaches the quote-guard), but also turns root-level
   `"a: b` and `'k': v` from mappings into scalars and changes which rule
   classifies `"a": "b" x`. Either is a normative §4.1 edit bearing on D2 and
   §11.2.3, so it is left for the principal.

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
