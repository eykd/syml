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
**Primary Dependencies**: `parsimonious>=0.10,<0.11` (PEG), which compiles
every grammar atom with the third-party `regex` module and requires it.
syml's own direct `regex>=2024.11.6,<2025` line is unused by `src/`, and its
cap has no Python 3.14 wheel, so this feature removes the line (Contract 09,
red-team pass 26) — see Constitution Check, principle V.
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
throughput. Every per-line and per-key step must stay O(1) amortized, because
§13.4's size limits are deferred and nothing else bounds input size. Red-team
pass 16 found the duplicate-key scan quadratic and made it a dict lookup
(Contract 03); pass 18 cut quoted-value lexing from about 1 KB of parse
nodes per character to one node per run, and pass 26 to five nodes per
quoted value, escape-dense ones included (Contract 02). Pass 26 also
stopped every node from keeping its parse node. Peak memory is still a
few hundred bytes per input byte, which Contract 09 note 13 documents.
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
| II. Type Safety | PASS | PASS | New public types (`Document`, `PositionMap`, `SymlData`, `SymlInput`, six exception classes) are fully annotated; `load`'s `IO[str] \| IO[bytes]` is checked without a cast (Contract 06), and so is `dumps` over a `dict[str, str]`, which needs the separate `SymlInput` parameter alias because `list`/`dict` are invariant (Contract 07, red-team pass 20). |
| III. Coverage and Lint Gates | PASS | PASS | FR-012 **removes** exemptions rather than adding them. Post-feature, the only permitted pragmas in `src/` are `if TYPE_CHECKING:` blocks. That is stricter than III's text, which still allows a pragma on a provably unreachable branch, and a permanent test enforces it; the first commit updates the guidance that still teaches the old pattern (Contract 09, pass 25). |
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
behaviour change violates IV as currently written. The full leaf ordering
(what else rides in that first commit, and what must land last) is stated
once, in Contract 09 § Leaf ordering (pass 25).

### Principle V — no new runtime dependency, no second leaf type

- **No new runtime dependency, and one fewer declared.** `regex` is declared
  but unused by `src/`. **Correction (red-team pass 26):** this bullet and
  research.md R-01's last alternative said Parsimonious compiles its atoms
  with `re`. Parsimonious 0.10.0 does `import regex as re` in
  `expressions.py` and requires `regex>=2022.3.15`, so every grammar atom
  already runs on `regex`, and `\p{White_Space}` would compile in one.
  D15's enumerated set stands anyway. It is the exact set D15 names, it
  does not tie the key class to the `regex` module's Unicode tables, and
  `re` and `regex` agree on it for every code point, as they do on `\Z`
  (verified). R-01's decision is unaffected; only its stated reason for
  rejecting `\p{White_Space}` was wrong, and research.md is left for the
  principal. syml's own `regex` line adds nothing Parsimonious does not
  already require, and its `<2025` cap blocks Python 3.14 wheel installs,
  so Contract 09 removes it. Complexity Tracking is therefore empty.
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
  positional `.args` prefix is preserved by `super().__init__(message, position,
  line_text, *extra)`, so `e.args[1]` keeps working. `DuplicateKeyError` and
  `MalformedQuotedStringError` append their extra attributes to `.args`, so
  every class survives `pickle` and `copy` (red-team pass 18, Contract 05).
- Parsimonious exceptions no longer escape `loads`/`load`; code catching
  `parsimonious.exceptions.IncompleteParseError` will stop seeing it.
- Absent values return `""` rather than `None` (FR-005) — the single largest
  behavioural break, and the one the library exists to make.
- `loads`/`load`'s static return type narrows from `list[Any] | dict[str,
  Any] | str` to `SymlData` (red-team pass 20). A typed caller's
  `r['k']['j']`, which checked against 0.6.2's `Any`, is a mypy error until
  each level is narrowed. Rejected alternative: keep the `Any`-bearing
  return, which cannot state FR-005's no-`None` invariant to a type checker
  and would make `dumps(loads(x))`'s round trip the only typed evidence of
  the data's shape.
- `ParseError`'s constructor requires `(message, position, line_text)`;
  `ParseError('msg')` is now a `TypeError`. `Source` no longer equals a
  non-`str` operand (`Source('1') == 1`; Contract 08, pass 20).
- Three more `Source`/`Pos` changes (red-team pass 23, Contract 08).
  `Source.from_node(pnode, filename)` becomes `from_node(pnode, line,
  position_map, filename)`, so a 0.6.2 caller's two-argument call is a
  `TypeError`. `Pos.from_str_index` and `Source.from_text` count only `\n`
  as a break, so text holding U+2028 or U+0085 gets different line numbers.
  `Source + str` counts the joining `\n` in `end.index`. Rejected
  alternative for `from_node`: keep the two-argument form beside a new
  per-line constructor. The old form cannot produce a correct position
  under per-line lexing, where `pnode.full_text` is one line, so keeping
  it keeps a wrong answer. The other two are §13.3 and arithmetic
  corrections, and no 0.6.2 caller could rely on the old results.

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
└── utils.py              # DELETED (Contract 01, pass 25): no caller left in src/

tests/
├── test_preprocess.py    # NEW
├── test_parsers.py       # TestSymlParser's fixture goes; two documents re-indented (Contract 03, pass 26)
├── test_nodes.py         # currently 0 bytes; populated (FR-017)
├── test_quoting.py       # NEW
├── test_serializer.py    # NEW
├── test_exceptions.py    # NEW
├── test_basetypes.py
├── test_utils.py         # DELETED with utils.py (pass 25)
├── test_api.py           # NEW — Contract 06: loads/load/parse (pass 25)
├── test_fixture_escapes.py # NEW — the acceptance fixture decoder's rows (pass 25)
├── fixture_escapes.py    # NEW helper, not collected — decode_fixture (pass 25)
├── serialization_corpus.py # NEW helper, not collected — US7 CORPUS (pass 25)
├── test_spec_examples.py # NEW — extracts fenced syml blocks from the spec (R-08)
└── tools/                # unchanged

tests/acceptance/
├── conftest.py           # + the shared step calling tests/fixture_escapes.py (R-05, pass 25)
└── test_us<nn>_<slug>.py # pytest-bdd bindings, marked `acceptance`

specs/acceptance-specs/
└── US<NN>-<slug>.feature # Gherkin, created by /sp:05-tasks

docs/glossary.md          # seven entries refreshed, four added (Contract 09)
SYML-SPECIFICATION.md     # relabelled 1.0; §11.3, §13.4, §4.5, §11.2.3 edits (Contract 09)
SYML-SPEC-REVIEW.md       # title + subject: reviewed text was the pre-release draft (Contract 09)
CHANGELOG.md              # NEW — migration notes (FR-015); pinned, not README (pass 25)
README.md                 # + serializer section, link to CHANGELOG (Contract 09)
todo.txt                  # retired (FR-016)
pyproject.toml            # version = "1.0.0"; direct `regex` line removed (Contract 09, pass 26)
.specify/memory/constitution.md  # amended to v2.0.0 (FR-019); III's stale parenthetical too (pass 25)
CLAUDE.md                 # principle-IV restatement + pragma bullet first; "conforms" last (Contract 09)
.claude/skills/pytest-unit-testing/SKILL.md  # pragma section, first commit (Contract 09, pass 25)
.claude/skills/{beads-task-chains,compound}/SKILL.md  # todo.txt references, with FR-016
```

**Module homes and import direction (red-team pass 17).** Every helper a
contract calls has exactly one home, and runtime imports run one way only.
In dependency order — `basetypes`, `exceptions`, `preprocess`, `nodes`,
`parsers`, `serializer`, `__init__` — each module imports at run time only
modules listed before it (plus `quoting`, which imports nothing from
`syml`; `utils` is deleted, pass 25). A name used only in an annotation from a module further
right is imported under `if TYPE_CHECKING:`.

| Module | Defines (new or changed) |
| --- | --- |
| `basetypes.py` | `Pos`, `Source` (+ `from_node`), `StrPath`, `Line`, `pos_at`, `SymlData`, `SymlInput` (re-exported by `__init__`) |
| `exceptions.py` | the seven classes, `error_message` |
| `preprocess.py` | `PositionMap`, `Document`, `preprocess`, `split_lines_lf`, `is_blank`, `original_line`, `encoding_error` |
| `quoting.py` | `decode_single_quoted`, `decode_double_quoted`, `diagnose_malformed`, `QuotedStringDefect` |
| `nodes.py` | the node classes; `fail_to_incorporate_node` |
| `parsers.py` | `GRAMMAR_TEXT` (the transcribed §4.1 text, pass 25), `GRAMMAR` (`Grammar(GRAMMAR_TEXT)`), `SymlParser`, `parse`, `find_first`, `raise_trailing_content` |
| `serializer.py` | `dumps`, `dump`, `structure_matches`, `key_is_representable` |

`Line` and `pos_at` sit in `basetypes.py`, not `preprocess.py`, because
`Source.from_node` calls `pos_at` at run time while `preprocess` builds `Pos`
at run time; placed in `preprocess.py` they made the two modules import each
other (Contract 01).

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
   single-line double-quoted string using escapes. A shared step in
   `tests/acceptance/conftest.py` decodes it with an explicit, audited
   unescape table — **not** `codecs.decode(..., 'unicode_escape')`, which
   round-trips through latin-1 and mangles the non-ASCII content US2/US3/US8
   fixtures require. The table is exactly these eight sequences, and this list
   supersedes the shorter one in research.md R-05 (pass 16):

   | Sequence | Decodes to | Needed by |
   | --- | --- | --- |
   | `\n`, `\t`, `\r` | LF, TAB, CR | every multi-line fixture; US2.3–5, US3.5–6 |
   | `\\` | one backslash | SYML-level escapes: US6.2 `'hello\\nworld'`, US6.7 `"a\\xb"` |
   | `\"` | `"` | every double-quoted SYML value inside the double-quoted step string |
   | `\xHH` | U+00HH | the canonical trailing space `\x20` (US3.2, US3.7, US4.4); `\x01` (US3.9) |
   | `\uXXXX` | U+XXXX | `\ufeff` (US2.1–2, US8.2), `\u2028` (US2.7, US8.4), `\u00a0` |
   | `\UXXXXXXXX` | U+XXXXXXXX | astral-plane content |

   Anything else after a backslash **raises**, so a mangled fixture fails
   loudly instead of loading as something else. R-05's list had no `\xHH`,
   which would have rejected every `\x20` fixture, and an earlier version
   of this note listed two literal, invisible characters where `\ufeff` and
   `\u2028` were meant. The decoder is fixture plumbing, not SYML's
   §4.7 decoder. `\ud800` therefore decodes to a lone surrogate without
   complaint. No acceptance fixture needs one: US6.7's `"\\ud800"` is a
   literal SYML escape, and the US7 corpus is Python (note 2).
   **Two levels of escaping are visible in the source**. US6.7's document
   `k: "a\xb"` (SYML text with a literal backslash) is written
   `Given a SYML document "k: \"a\\xb\""`. US3.9's `a\x01b: v` (a real
   U+0001) is written `"a\x01b: v"`.
   **SYML text never goes in an `Examples:` table cell**: gherkin-official
   (29.0.0, pinned via pytest-bdd 8.1.0) unescapes cells before pytest-bdd
   substitutes them — `\\` becomes `\`, `\n` a real newline, `\|` a `|` — while
   inline step text arrives raw (verified with the installed parser). A cell
   `a\\: b` would reach the decoder as `a\: b`: double-decoded or rejected.
   Fixtures live only in inline step strings, decoded exactly once.
   **Where the decoder lives, and what tests it (pass 25).** Placed in
   `tests/acceptance/conftest.py`, the "anything else raises" rule would run
   under no test at all: the unit run `--ignore`s that directory, coverage
   omits `conftest.py` and measures only `src/` and `tools/`, and an
   acceptance scenario only ever feeds it valid fixtures. It lives in
   `tests/fixture_escapes.py` (`decode_fixture(s: str) -> str`; not collected,
   inside the mypy file set), imported by the acceptance conftest's shared
   step, with `tests/test_fixture_escapes.py` in the unit run asserting the
   eight rows above and a `ValueError` for an unknown escape (`\q`) and a
   trailing lone backslash.
   **Import form (pass 25, verified).** `tests/` and `tests/acceptance/` have
   no `__init__.py`, and the two runs see different `sys.path`s. `from
   tests.fixture_escapes import …` imports under pytest but makes mypy
   report `tests/fixture_escapes.py` as "found twice under different module
   names" (`mypy_path` already holds `./tests`). A bare `from
   fixture_escapes import …` passes mypy and the unit run but fails under
   `just acceptance`, whose prepend import mode adds `tests/acceptance/`,
   not `tests/`. So pyproject's `[tool.pytest.ini_options] pythonpath`
   becomes `[".", "tests"]`, which `-o addopts=""` does not touch, and
   every import of `fixture_escapes` and `serialization_corpus` uses the
   bare form. With that, mypy and both runs pass.
   **The empty document needs its own binding (pass 25).** US00's step
   pattern, `parsers.parse('a SYML document containing "{text}"')`, cannot
   match `""`: `parse`'s `{text}` needs at least one character, so
   `Given a SYML document ""` fails as `StepDefinitionNotFoundError`, which
   is also the ATDD RED marker and so reads as "not bound yet" (verified
   against pytest-bdd 8.1.0). Bind the shared step with
   `parsers.re(r'a SYML document "(?P<text>.*)"')`, or write US4.2 as
   `Given the empty document`. Escapes (`\"`, `\\`, `\x20`, `\ufeff`), a
   leading `#` inside the step string, and corpus-id outlines were all
   verified to bind as described.
2. **US7 scenario 1 is a property, not an example.** `loads(dumps(x)) == x` over
   a representable corpus: write it as a `Scenario Outline` whose `Examples:`
   rows carry **corpus identifiers** that index a shared Python corpus
   (Contract 07 lists what the corpus must contain, and pins its home as the
   module `tests/serialization_corpus.py`, not a fixture; pass 25), not the
   strings themselves and not one row. Pass 4 added backslash-bearing entries (`a\: b`,
   `a: 'b" \c`) that note 1's cell hazard would corrupt.
3. **US9's nine scenarios are repository-inspection steps**, not parser tests —
   they bind against file contents, `importlib.metadata.version('syml')`, and
   `git tag --list`. They belong in the acceptance suite, where a non-parser
   Given/When/Then reads naturally, rather than in the unit run.
   Shelling out trips ruff in `tests/`, whose per-file ignores are only
   `S101`, `D1`, `INP001`, `ARG001`: `import subprocess` is `S404` (preview),
   the call is `S603`, and a bare `git` is `S607` (pass 25). The US9 binding
   and Contract 02's `python -W error -c "import syml"` test take line-level
   `noqa`s with the justification `tools/` already records, rather than a
   directory-wide ignore.

**Random order (pass 25).** `just acceptance` runs `-p no:random_order`, so
the acceptance fixture rules never meet a shuffled order. They would
survive one: the `context` fixture is function-scoped and nothing else
carries state (verified with forced seeds). The unit suite does run
shuffled; an assembly of every Contract 01-08 test obligation passed
under five `--random-order-seed`s with no order dependence.

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
  converts **within the same method** (Contracts 04, 05). *(Corrected by
  pass 17: the converting method is `visit_quoted_value`, which calls the
  decoder; a parent's `except` never runs.)* The subclass
  constructors now take their extra attributes keyword-only
  (`*, escape, code_point` / `*, key, first_position`), so `.args` stays three
  elements. *(Reversed by pass 18: keyword-only extras break `pickle` and
  `copy`, which call `cls(*e.args)`; the extras are now positional and in
  `.args`.)* data-model §5's stale `contracts/errors.md` link now points at
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

### Pass 10 (2026-09-23, outer iteration 7): incorporate_node's missing receiver

R-09's stranded-prefix claim and the `\r\r\n` / trailing-bare-`\r` line
boundaries still hold, unaffected by this pass.

- **Contract 05's inline-incorporation rule named no receiver (Low).** Rule 2
  wrote `incorporate_node(value, self.doc)` as if it were a free function,
  the only call in Contracts 02/03/05 written that way — every other site is
  `<node>.incorporate_node(<candidate>, doc)`. Today's `parsers.py` shows
  `visit_key_value` building an empty `section` and calling
  `section.incorporate_node(value)`, and `visit_list_item` building an empty
  `li` and calling `li.incorporate_node(value)` — uniformly, for a leaf value
  or a nested `structure` alike. `key_value`'s own value slot is only ever
  `quoted_value`/`data` (never `structure`, per Contract 02's grammar), so
  `section`'s call always resolves in one step; `li`'s can recurse into
  §9.2's full algorithm for `- key: v` / `- - x`. **Mitigation**: Contract 05
  now names both receivers explicitly and notes which one can recurse.

### Pass 11 (2026-09-23, outer iteration 7): who assigns node state

Swept Contracts 01-09 and data-model as one program. R-09's stranded-prefix
claim and the `\r\r\n` / trailing-bare-`\r` boundaries still hold
(re-probed: `k: "a" x` strands at 7, right after the quote and its space;
`a\r\r\nb\r` has three breaks both before and after normalization).

- **No node's `level` was set before the inline `incorporate_node` calls
  (High).** Contract 05 rule 2 has `visit_list_item` call
  `li.incorporate_node(value, self.doc)` inside the visit, and Contract 03's
  table compares `node.level > self.level`. But no artifact said who sets
  `level` on a fresh `KeyValue`/`ListItem`/`TextLeafNode`. Today the only
  assignment is `visit_line`'s `set_level(indent.level)`, which runs *after*
  those calls. So for `- key: v` both operands are `None` at the moment of
  the call, and `None > None` is a `TypeError`. That is not in
  `unwrapped_exceptions`, so a `VisitationError` would escape `loads`
  (FR-009). Today's code hides this with `node.level is None or …` guards and
  `node.set_level(self.level)` inheritance, and that inheritance is M23, the
  bug R-11 removes. **Mitigation**: `level: int` is a required constructor
  argument, set by the building `visit_*` from its own line-local
  `pnode.start`. Contract 02 now has a per-node table and a worked trace of
  `-   name: Alice\n  role: admin` (US1.8). `set_level`, `visit_line`'s level
  write, `IndentNode`, and the `None` guards are deleted. data-model §3.1
  matches.
- **`anchor_level` and `baseline` had no assignment site either (High).** Same
  defect class. `visit_text` cannot know whether a bare line will be a root
  scalar, a block value, or a continuation. **Mitigation**: a new `inline:
  bool` field, set by `visit_key_value`/`visit_list_item`. The accepting
  node's `add_node` assigns `anchor_level`/`baseline`: `KeyValue`/`ListItem`
  use their own level, with baseline `None` if inline and the leaf's level if
  block; `Root` keeps the defaults `-1`/`0`. `TextLeafNode.add_node` fixes an
  unset baseline and returns `self`, so the tip is unchanged (§9.3).
  Contract 03, data-model §3.1, and Contract 09's field list match.
- **D6 had no implementation home, and Contract 02 mislabelled `key:␠`
  (High).** The table said `key:␠` lexes as `section`. In fact it lexes as
  `key_value`'s second alternative with an **empty** `text` (verified;
  `section`'s `&eol` fails on the space), and `-␠` likewise. Contract 05
  rule 2 attached every inline value "uniformly". An empty leaf would
  therefore close the node, and US3.7 (`key:␠\n  nested: content`) would
  raise `OutOfContextNodeError`. **Mitigation**: `visit_key_value` and
  `visit_list_item` skip incorporating an empty **unquoted** leaf (§9.3's
  normalization). `key: ""` is still a real child. Contract 02's rows are
  corrected, and the D6 fixtures (`-␠\n  x`, `- - ␠\n    x`, and
  `key: ""\n  x: y`) are worked cases and test obligations. This transcribes
  D6 and does not change it.
- **Contract 05 named a `section` child that is not on the `key_value` path
  (Low).** `key_value` contains `key_colon`, and `section` only matches a
  valueless line. Reworded.

### Pass 12 (2026-09-23, outer iteration 8): `Root`'s own required field

Swept Contracts 01-09 and data-model as one program per the orchestrator's
targets. R-09's stranded-prefix claim and the `\r\r\n` / trailing-bare-`\r`
boundaries were re-verified once more (`k: "a" x` strands right after the
quote and its trailing space; `a\r\r\nb\r` counts three breaks both before
and after normalization) and still hold.

- **`Root(...)` was constructed with no `level` (Medium).** Pass 11 made
  `level: int` a required constructor argument with no default, and Contract
  02's "Who sets `level`" table already said `Root | the per-line loop | 0`.
  But both pseudocode construction sites — Contract 02's entry-point loop and
  Contract 03 § Automatic container creation — wrote
  `Root(pnode=None, source=Source(...))`, omitting `level` entirely. As
  written, that call cannot type-check against pass 11's own rule.
  **Mitigation**: both sites now read `Root(pnode=None, level=0,
  source=Source(...))`, matching the table.
- **data-model §3's tree diagram mislabelled `Root` (Low).** The comment
  `Root # level 0, anchor_level -1` implied `Root` carries an `anchor_level`
  field; that field belongs to `TextLeafNode` only (§3.1), and the `-1`
  value it names is the *root-scalar's* `anchor_level` (§3.3's table), not
  `Root`'s. Trimmed to `Root # level 0`.
- Re-verified: `TextLeafNode`'s inline-vs-fixed acceptance operators
  (`level > anchor_level` before fixing, `level >= baseline` once fixed) and
  the D13 isinstance-only acceptance are stated identically in Contract 03's
  "TextLeafNode continuation" table and data-model §3.3; no drift found there.

### Pass 13 (2026-09-23, outer iteration 8): hand-executing the acceptance examples

Treated Contracts 02 + 03 as one program and hand-executed every US1, US3,
US4 and US6 acceptance example through it, plus §5.3's and §6.3's worked
examples. All produce the specified tree or error (US1.1-10, US3.1-9,
US4.1-4, US6.5/6/8/9/10, `- - ␠\n    x`, §6.3's deep nesting). R-09 still
holds (the only partial `line` match is a closed `quoted_value` plus ` *`,
reached via `key_value`'s first alternative or `value`'s second); `\r\r\n`
and a trailing bare `\r` still count identically before and after
normalization.

- **A root scalar's indented head line lost its indentation (High).** §5.3
  is explicit: "`  hello\nworld` is `"  hello\nworld"`, and the one-line
  document `  hello` is `"  hello"`." Contract 03 rendered only continuation
  children with `' ' * (level - baseline)`; the head rendered as its stored
  `Source`, which starts at the `text` token (column 2). The result was a
  silently wrong value, and no user-story scenario exercised it (US1.6's head
  is at column 0). **Mitigation**: Contract 03 gives `TextLeafNode.as_data`
  in full, prefixing the head with `' ' * (level - baseline)` **unless it is
  inline** — an inline head shares its line with `key:`/`-` and must not be
  prefixed (`key: a\n  b` would otherwise gain three spaces). The prefix is
  non-zero only for a root scalar, since a block head has `level ==
  baseline`. `as_source()` widens the head's span left by the same count,
  exact in original coordinates because the span is the line's space-only
  indent run. Contract 08's continuation-span rule and property test, and
  data-model §3.3/§4, now say the root-scalar `start` is the first preserved
  space. `dumps` is untouched: §11.2.4 already makes such a root scalar
  unrepresentable. This implements D11 and §5.3 as written; no decision
  changes.
- **`KeyLeafNode.key` still called the retired `Source.from_node` signature
  (Medium).** Today's property rebuilds `Source.from_node(self.pnode,
  filename=...)`. Contract 08 changed `from_node` to four arguments and pass 9
  made `source` a constructor field, but no contract retired this second
  caller. Every key's `Source` flows through it, including
  `Mapping.can_add_node`'s duplicate compare. **Mitigation**: Contract 03
  deletes the property; `KeyLeafNode.as_source()` returns the stored
  `self.source` and `as_data()` its text.
- **An absent value's empty `Source` had no position (Medium).** Contract 03
  and data-model §3.5 promised "an empty `Source`" for a childless
  `KeyValue`/`ListItem` but pinned a position only for `Root`. Contract 08's
  editor use case needs one. **Mitigation**: zero-width at the container's
  own `source.end` (just past `key:`'s colon, `-`'s marker, or `-␠`'s
  consumed space). `Root`'s existing `Pos(0, 1, 0)` span is the same rule.
  Both are test obligations.

### Pass 14 (2026-09-23, outer iteration 9): a reference prototype, end to end

Built a throwaway prototype of Contracts 01-04 and 07 exactly as written
(grammar transcribed, per-line loop, acceptance table, `add_node`
assignments, D6 skip, quote-guard, stranding check, `to_original`,
`original_line`) and ran it three ways. R-09 re-checked by construction (the
only partial `line` match is a closed `quoted_value` plus ` *`); `\r\r\n`
and a trailing bare `\r` still count identically before and after
normalization (`\ufeffa: 1\r\r\n  b: 2` reports `b` at index 10, line 3,
column 2).

- **Every specification example agrees.** R-08's extraction rule (a
  ` ```syml ` block followed by `**Output:**`) finds exactly 53 blocks; the
  prototype's result equals the stated output for all 53, including every
  `ERROR:` class. §3.1's block is not among them: its marker is
  `**Output (as JSON-like structure):**`, so the 53-block floor excludes it.
  The prototype matches that output too.
- **Every `ParseError` anchor holds on BOM + CRLF documents.**
  `TabIndentationError`, `OutOfContextNodeError`, `DuplicateKeyError`, and
  `MalformedQuotedStringError` (guard, trailing content, surrogate) were each
  raised on line 1 of a BOM document and on a later CRLF line. In every case
  `line_text[position.column]` and `original[position.index]` are the anchor
  character. `EncodingError` on `b'\xef\xbb\xbfa: \xc3\xa9\r\nc: \xff'`
  derives index 10 (from byte offset 13), line 2, column 3, with `line_text`
  `'c: '`.
- **Keys holding a control character corrupt the round-trip (High).**
  Contract 07 transcribed §11.2.3's list (whitespace, `:`, empty, leading
  `#`/`//`). But `key`'s class also excludes C0 and C1 controls (§4.5), so
  `dumps({'a\x01b': 'v'})` emits `a\x01b: v`, which `loads` reads back as the
  root scalar `'a\x01b: v'`. Same for `\x7f` and `\x9f`, and for `\x1c` under
  a Python-`\s` reading of "whitespace". This is silent corruption of a MUST.
  **Mitigation (Contract 07)**: a key is representable iff
  `GRAMMAR['key']` matches the whole key and the key begins with neither `#`
  nor `//`. The grammar is then the one definition, so the list cannot drift
  from §4.5. §11.2.3's own closing clause ("rather than emit a key that would
  not read back correctly") already requires this; Contract 09 adds one
  clarifying sentence to §11.2.3, as R-01 did for §4.5.
- **A document whose first character is U+FEFF loses it (High).** §9.0 step
  1 strips one leading BOM, so `dumps('\ufeffx')` and `dumps({'\ufeffk':
  'v'})` read back as `'x'` and `{'k': 'v'}`. No §11.2.3/.4 condition
  covers them, and neither the root scalar nor the key is anything else
  unrepresentable. Only the document's first character is exposed: a root
  list starts with `-`, and any later key sits after a line break.
  **Mitigation (Contract 07)**: when the rendered document's first
  character is U+FEFF, `dumps` prepends one U+FEFF. §9.0 strips exactly that
  one (Contract 01's `"\ufeff\ufeffkey: v"` row), so the value's own mark survives.
  This needs no spec edit: the output format is an implementation choice,
  and the round-trip MUST is met. Raising `UnrepresentableValueError` was
  considered and not applied. It would be a new unrepresentable condition in
  §11.2.3/.4, which is normative, for values the specification currently
  requires `dumps` to serialize. That is open item 5 below.
- **`ParseError.message` and the filename disagreed (Medium, Congruence).**
  data-model §1 says `filename` is "carried into every … `ParseError`
  message", and Contract 06's test obligations assert it. But every raise
  site in Contracts 03 and 05 passes a fixed string, and `load` resolved the
  filename only after `read()`, so `EncodingError` could never carry it.
  `ParseError` has no `filename` attribute, and `Pos` has none either, so the
  message is the only place a caller of `load` can learn it. **Mitigation**:
  Contract 05 defines `error_message(description, filename)`, and every
  raise site uses it. Contract 06's `load` now resolves `filename` before
  `read()`.
- **Two Low fixes.** Contract 01's tab-scan table was split by a paragraph,
  so its last three rows rendered as prose. The paragraph now follows the
  table. Contract 08's `Source("foo")` cannot be constructed, because
  `Source` has four required fields. The test obligation now builds it with
  keywords.

### Pass 15 (2026-09-23, outer iteration 9): second-order check of pass 14

No Critical or High finding. The key probe is never a `structure` probe, so
it cannot meet rule D's `RecursionError` catch or the `\u003a` fallback. The
U+FEFF prefix is decided on the rendered output, so a root scalar such as
`'\ufeff- x'` is probed and reloaded as the same line text, and
`'\ufeffk: v'` stays unrepresentable under §11.2.4(a). `error_message` has a
filename in scope at every raise site: `preprocess`'s argument, `doc.filename`
in the visitor and the tree, and `load`'s early resolution.

- **`utf-8-sig` defeats the U+FEFF prefix (Low).** A file written by `dump`
  and reopened with `encoding='utf-8-sig'` loses one mark to the codec and
  the other to §9.0. Contract 07 now tells the `dump` docstring to say so.

### Pass 16 (2026-09-23, outer iteration 10): the prototype rebuilt against today's contracts

Brought the pass-14 prototype up to the contracts as they stand after
iterations 9 and 10. Contracts 01–04 had not changed since, and Contract 07
was re-transcribed in full: the grammar key probe, the U+FEFF prefix, rule D
by prefix match with its `RecursionError` catch, the `\u003a` fallback, and
§11.2.4(a)–(e). All 53 specification examples still agree (the extraction
floor holds at 53). So do 56 user-story and contract-table examples, which include every
parser-level scenario in US1–US4 and US6. R-09 and R-02 sanity: `\r\r\n` and
a trailing bare `\r` keep the break count equal before and after
normalization, and `\ufeffa: 1\r\r\n  b: 2` still reports `b` at
`Pos(10, 3, 2)`. Round trip: 784 values, built from the spec examples plus
adversarial strings, each placed at the root, as a mapping value, as a list
item, as a list-item mapping value, and nested. The strings covered U+0085,
U+2028, U+2029, U+3000, U+00A0, and U+FEFF in values and keys, whitespace-only
strings, lone surrogates, a 200,000-character string, a 100,000-character
key, `'- ' * 200 + 'x'`, and nested empty containers. 659 round-trip and are
idempotent, and 125 raise `UnrepresentableValueError`. Every one of the 125
falls under a condition in §11.2.2–.4 or pass 14's key rule. None fails.

- **The duplicate-key check is quadratic (Medium, Performance).** Contract 03
  scanned `self.children` for every incoming key. Measured on the prototype:
  64,000 keys (a 630 KB document) took 24 s. §13.4's size limits are deferred
  past 1.0, so nothing bounds this, and a hostile document of about 1 MB
  exhausts CPU. It is not a regression against 0.6.2, whose whole-document
  parse is slower still (1,000 keys take 0.26 s, 8,000 did not finish in 10
  minutes), which is why this is not rated High. **Mitigation (Contract 03,
  data-model §3.1)**: `Mapping.keys: dict[str, KeyValue]` is filled in
  `Mapping.add_node`, and `can_add_node` does a lookup after the level gate.
  The same 64,000 keys now load in 1.4 s, and all example suites still
  agree.
- **The rule-D probe let a third-party exception out of `dumps` (Medium).**
  `GRAMMAR['structure'].match(s)` *raises* parsimonious's `ParseError` when
  nothing matches, which is the case for every ordinary list item (`hello`,
  `#x`, `''`). Contract 07 stated only the `RecursionError` catch for this
  probe, and its "no parsimonious exception leaves `dumps`" obligation was
  scoped to keys. **Mitigation (Contract 07)**: `structure_matches` is now
  given as code with both catches, and the test obligation covers every
  value.
- **The fixture decoder could not decode `\x20` (Medium, Congruence).**
  Strategy note 1 called `\x20` canonical. R-05's audited table has no
  `\xHH`, and the decoder raises on anything outside its table. Note 1 also
  listed a literal U+FEFF and a literal U+2028, both invisible, where escapes
  were meant, and it omitted `\\` and `\"`. Without those two, US6's SYML-level
  escapes (`'hello\\nworld'`, `"a\\xb"`) cannot be written.
  **Mitigation**: note 1 now carries the eight-sequence table, supersedes
  R-05's list, and shows the two escaping levels with worked forms for US6.7
  and US3.9. The table covers every string the acceptance fixtures need. The
  US7 corpus stays in Python.
- **`dump` could leave a truncated but loadable file (Medium).** Contract 07
  did not say whether `dump` streams. A streaming `dump({'a': '1', 'b': {}},
  fp)` writes `a: 1` before raising, and the file then loads as `{'a': '1'}`
  with no error. **Mitigation (Contract 07)**: `dump` is one
  `write(dumps(data))`, so nothing is written when `dumps` raises.
- **The `dumps` docstring was a one-line stub (Low, Congruence).** Contract 07
  pointed at it for the `\u003a` fallback, the format choices, and the U+FEFF
  prefix, but the docstring shown said none of that (noted in commit e3f8f16).
  The docstring now says all three, and `dump`'s says it writes once.
- **Two Low pins (Contract 07).** A non-`str` key is a `TypeError` from an
  explicit check. Today it is one only by accident, from `re`'s "expected
  string or buffer". `dumps('')` is `''`, the empty document, with no
  trailing newline.
- **Invisible characters (Low).** Contracts 01, 06, 07, and 08,
  data-model.md, and this plan had literal U+FEFF and U+2028 inside
  backticked Python-literal cells. A reader sees `"key: value"` where the
  input is `"\ufeffkey: value"`, and Contract 01's corpus note read "and `` ``".
  All of them are now `\ufeff` / `\u2028` escapes.

### Pass 17 (2026-09-23, outer iteration 11): Parsimonious's visit order

Treated Contracts 01-09 and data-model as one program again, this time
checking each contract's *mechanism* against Parsimonious's `NodeVisitor`
rather than its intended outcome. R-09 holds by construction: the only `line`
path that can stop short of end of line is `quoted_value ~" *"`; every other
path ends in `text` or `&eol`. R-02 holds: `a: b\r\r\nc` normalizes to
`a: b\n\nc` with `crlf_indices == (5,)`, three lines on both sides, and a
trailing bare `\r` is one break on both sides.

- **Decoder defects escaped `loads` as `VisitationError` (High).** Pass 7
  had `visit_key_value` / `visit_list_item` catch the private
  `QuotedStringDefect` "inside the same method". But Contract 02 has
  `visit_quoted_value` build the quoted `TextLeafNode`, and Contract 08 needs
  its `Source.text` decoded, so the decoder runs in `visit_quoted_value`.
  Parsimonious's `visit` runs `method(node, [self.visit(n) for n in node])`:
  a child's exception is wrapped by the child's own `visit` frame before the
  parent's method body starts, so the parent's `except` never runs. Verified
  against the transcribed grammar: with the catch in the parent,
  `k: "\ud800"`, `- "\ud800"`, and `- - k: "\U00110000"` all escape as
  `parsimonious.exceptions.VisitationError` (FR-009), and neither parent
  method executes. Two Contract 04 table rows would have failed. The
  pass-14/16 prototypes must have converted in `visit_quoted_value`, so they
  tested the intended behaviour, not the written mechanism.
  **Mitigation (Contracts 02, 04, 05, 08)**: `visit_quoted_value` decodes,
  converts `QuotedStringDefect` to `MalformedQuotedStringError` itself
  (anchor: `to_original(pos_at(self.line, node.start))`, the opening quote),
  and stores the decoded text with `dataclasses.replace(source, text=...)`.
  With the catch there, all three inputs raise the `ParseError` subclass.
  `QuotedStringDefect` stays out of `unwrapped_exceptions`. Pass 1's
  precedence rule still holds (`k: "\ud800" x` is trailing content), because
  stranding is checked before any visit. Contract 05 gains a test obligation
  for the decoder rows at `key:`, `- `, and `- - k:` positions.
- **`basetypes` and `preprocess` imported each other (Medium).**
  `Source.from_node` (`basetypes.py`) calls Contract 01's `pos_at`
  (`preprocess.py`) at run time, and `preprocess` constructs `Pos`
  (`basetypes.py`) at run time. That is a circular import, so the second
  `from … import` fails on a partly initialized module. No contract said
  where `original_line`, `error_message`, `find_first`,
  `raise_trailing_content`, or `GRAMMAR` live either. `original_line` placed
  in `parsers.py`, next to its first definition in Contract 05, would have
  made `nodes` and `parsers` import each other. **Mitigation**: `Line` and
  `pos_at` move to `basetypes.py` (Contract 01, data-model §2), and
  § Project Structure now gives every helper's module and the one-way import
  order.
- **Second-order check (no finding).** A quoted leaf built with
  `inline=True` in `visit_quoted_value` changes nothing downstream: D6's skip
  tests `quoted` and so never drops `key: ""`; `ContainerNode.add_node`'s
  inline/block branch is irrelevant for a leaf that accepts nothing; and the
  new import order has no cycle (`nodes` reaches `original_line` and
  `error_message` through modules listed before it).

### Pass 18 (2026-09-23, outer iteration 12): library behaviour under the error and quoting paths

Treated Contracts 01-09, data-model, and this plan as one program, checking
each mechanism against the library it leans on (codecs, `BaseException`
pickling, Parsimonious's repetition nodes) rather than the outcome a
UTF-8, single-process prototype sees. R-09 sanity: `k: "a" x` still strands
at 7 of 8, just past the quote and its space. R-02 sanity: `a\r\r\nb\r` has
three breaks both before and after normalization.

- **`EncodingError`'s derivation raised from inside `load`'s handler (High).**
  Contract 05 step 1 decoded the failing prefix with a hard-coded
  `.decode('utf-8')` and called that "always succeeds". That holds only when
  the failing codec was UTF-8. Pass 5 made `load` catch a text handle's
  `UnicodeDecodeError` too, and a text handle decodes with its own encoding.
  `open(p)` uses the locale's, which Contract 06 already notes is not UTF-8
  on Windows before Python 3.15. Over a UTF-8 file containing `Á` (`C3 81`),
  a cp1252 handle fails at `0x81` (undefined in cp1252), so the prefix ends
  in the lone lead byte `0xC3`. Decoding it as UTF-8 raises a second
  `UnicodeDecodeError` inside the `except` clause. That escapes `load` on
  the default `load(open(p))` path of a supported platform, against FR-009.
  A `utf-16-le` handle fails the same way (verified for both).
  **Mitigation (Contracts 05, 06)**: decode the prefix with the codec that
  failed, `err.object[:err.start].decode(err.encoding, errors='replace')`.
  That codec already decoded exactly this prefix, so `replace` never fires on
  a real failure. It is an argument, not a branch, and for `load`'s own
  strict UTF-8 decode the result is unchanged. Contract 06 gains a cp1252
  row and test, and scopes "same `Pos` as the binary handle" to
  `encoding='utf-8'`, because `'utf-8-sig'` strips the mark before decoding.
- **Quoted values cost about 1 KB of parse nodes per character
  (Medium, Performance).** §4.1 prints the quoted bodies one character per
  repetition, and Parsimonious builds a node and a cache entry for each. A
  100,000-character value takes 66 MB (single) or 98 MB (double) and
  0.8-1.3 s to lex, against nothing unquoted, so a 1 MiB quoted line needs
  about 1 GB. §13.4's limits are deferred and nothing bounds it, the same
  situation as pass 16's quadratic key scan. It is also a regression, since
  0.6.2 read the same line as one regex match.
  **Mitigation (Contract 02)**: a third transcription-level substitution
  writes the negated classes as runs, `~"[^'\n]+"` and `~"[^\"\\\\\n]+"`.
  The language is the same. A brute force over 5.8 million lines
  (alphabet `'"\a :u0n-x`, after `k: `, `- `, and `k:`) found identical
  `match` ends and named-node spans. No visitor reads inside a quoted
  token. The same values now lex in about 1 ms. An as-printed oracle grammar
  in the tests pins the equivalence. No spec edit is needed, because §4.1's
  language is unchanged.
- **Two exception classes could not be pickled or copied (Medium).** Pass 7
  made `DuplicateKeyError`'s and `MalformedQuotedStringError`'s extras
  keyword-only to keep `.args` at three elements. `pickle`, `copy.copy`, and
  `copy.deepcopy` rebuild an exception as `cls(*e.args)`, and that call is
  then a `TypeError` (verified on both classes). Such an error raised in a
  `ProcessPoolExecutor` or `multiprocessing` worker cannot reach the parent
  process. **Mitigation (Contract 05, data-model §5)**: the extras are
  ordinary parameters appended to `.args`, and `ParseError.__init__` takes
  `*extra`. Raise sites still pass them by keyword. `e.args[1]` is still the
  `Pos`, which is all the Constitution Check promised. The round trips are a
  test obligation for every class.
- **`inline`'s setter was stated in two places (Low, Congruence).**
  data-model §3.1 and Contract 03's surface named only
  `visit_key_value`/`visit_list_item`, but pass 17's `visit_quoted_value`
  sets `inline=True` at construction. Both now say so.

### Pass 19 (2026-09-23, outer iteration 12): second-order check of pass 18

No Critical or High finding. The run atoms leave `diagnose_malformed`,
`find_first`, Contract 07's re-lex, and Contract 08's quoted spans unchanged:
none reads inside a quoted token, and the oracle compared every named node,
`escape_seq` included. Widening `.args` changes no `message` or `line_text`,
and nothing asserts `str(e)` or `len(e.args)`. R-09 and R-02 were not
touched.

- **`err.encoding` can name no codec (Low).** It is a free string, so a
  custom file-like can raise `UnicodeDecodeError('no-such-codec', …)` and
  pass 18's `.decode(err.encoding, …)` then raises `LookupError` (verified).
  Contract 05 falls back to UTF-8 with `errors='replace'` on `LookupError`.
  The branch is tested with a fake handle.
- **cp1252 reports as `'charmap'` (Low).** Decoding with it reads bytes
  0x80-0x9F as C1 controls, so `line_text` can differ from the handle's own
  reading (`€` becomes U+0080). Positions are exact, because every byte is
  one code point in both codecs. Contracts 05 and 06 now say so.

### Pass 20 (2026-09-23, outer iteration 13): typing, `Source`, and the output codec

Checked Contracts 03, 06, 07, 08, and 09 against what mypy, `io`, and the
existing `Source` code actually do. R-09 sanity: `k: "a" x` still strands at
7 of 8, and `- k: 'a'\tx` at 8 of 10. R-02 sanity: `a\r\r\nb\r` has three
breaks before and after normalization, and a trailing bare `\r` has one.

- **`dumps(data: SymlData)` rejects typed callers (High, Type Safety).**
  `list` and `dict` are invariant, so under mypy strict `dumps(cfg)` with
  `cfg: dict[str, str]` is an `arg-type` error, and so are `list[str]` and
  `dict[str, list[str]]` (verified). Only a literal or a value already typed
  `SymlData` passes. **Mitigation (Contract 07)**: the parameter is a
  separate alias, `SymlInput = str | list[Any] | dict[str, Any]`, which
  accepts all three and still rejects `dict[int, str]` and a tuple
  (verified). `SymlData` stays the return type. Both aliases move to
  `basetypes.py`: Contract 06 defined `SymlData` in `__init__.py`, which
  `serializer.py` precedes in pass 17's import order.
- **`loads`'s return type is a typing break (Medium, Congruence).** Under
  0.6.2's `dict[str, Any]` a typed caller's `r['k']['j']` checked; under
  `SymlData` it is a mypy error (verified). Added to the Principle VI list
  above, to Contract 06's change table, and to migration note 14.
- **`TextLeafNode.as_source()` had no mechanism (High, Congruence).**
  Contract 08 stated the outcome (`text == as_data()`, preserved indentation
  included), but the only composition on `Source`'s surface was `__add__`,
  which today's `as_source` uses and which joins with a bare `\n`. Kept as
  is, US1.3's shape gives `"first\nindented\nback"` against `as_data()`'s
  `"first\n  indented\nback"`. **Mitigation (Contract 03)**: `as_source`
  is written out beside `as_data`: the widened head's `start`, the last
  accepted line's `end`, and `text=self.as_data()`. No parse path calls
  `__add__`.
- **`Source.__eq__` equalled non-strings (Medium).** `str(self) ==
  str(other)` made `Source('1') == 1` and `Source('None') == None` true with
  unequal hashes (verified), which breaks Python's eq/hash rule and is
  broader than §10.3's "exactly as their text". **Mitigation (Contract
  08)**: `str` and `Source` operands only, else `NotImplemented`. R-07's
  interchangeability is unchanged. The same probe showed that `==` never
  checks a position, which is why the existing tests' position assertions
  are vacuous and `Source + 'x'`'s off-by-one `end.index` (and `Source + ''`'s
  `IndexError`) went unnoticed. Contract 08 now requires field-by-field
  position assertions and corrects the `str` branch.
- **§11.1's strict UTF-8 holds on the bytes path only (Medium).** Contract
  06's cp1252 row used `Á`, whose second byte `0x81` is undefined in cp1252.
  For `é` both bytes are defined, and a cp1252 text handle returns
  `{'key': 'Ã©'}` with no error (verified). `load` never sees the bytes, so
  this is documented, not prevented: Contract 06 scopes the guarantee and
  pins the row, and migration note 11 no longer says "from a text handle
  too".
- **`dump` writes through the handle's codec (Medium).** §13.3 makes SYML
  documents UTF-8, but a cp1252 handle writes `é` as `\xe9`, which
  `load(open(p, 'rb'))` rejects. `surrogateescape` writes a lone surrogate as
  a raw byte, and a `utf-8-sig` writer adds a third U+FEFF that a binary
  `load` keeps (all verified). Contract 07 now says so in `dump`'s docstring
  and a codec table, and the US7.9 round trip names `encoding='utf-8'`. The
  single-write rule survives the codec path, because `TextIOWrapper.write`
  left the buffer at `b''` on `UnicodeEncodeError` (verified). Raising on a
  non-UTF-8 `file_obj.encoding` was considered and not adopted (Contract 07
  gives the reasons).
- **Two Low congruence fixes.** R-04's derivation had no named home and two
  call sites in `load`: it is now `encoding_error(err, filename)` in
  `preprocess.py` (Contract 05). Migration note 9 now says `ParseError`'s
  constructor needs three arguments and `.message` carries the filename, and
  note 11 says `filename` defaults from `file_obj.name`. Contract 09's
  glossary row for `OutOfContextNodeError` says what replaces the stale
  sentence.

### Pass 21 (2026-09-23, outer iteration 13): second-order check of pass 20

No Critical or High finding. Every reference to the dump parameter now says
`SymlInput`, and `SymlData` remains only as a return type. The four
`__add__` statements (Contract 08's surface and change row, Contract 09's
FR-017 row, data-model §4) agree, and Contract 03's `as_source` is the only
composition path. `as_source` handles an inline head whose `baseline` is
still `None` (it never subtracts it), a quoted leaf (no children, decoded
`text`), and a root scalar's indented head. `NotImplemented` from a
`bool`-annotated `__eq__` is accepted by mypy.

- **Exports need `__all__` (Low).** pyproject sets `no_implicit_reexport =
  true` and mypy covers `tests/`, so re-exporting `SymlData`, `SymlInput`,
  and the seven exception classes from `__init__.py` by plain import would
  make every `from syml import …` in the tests a mypy error. Contract 06 now
  requires `__all__`.

### Pass 23 (2026-09-23, outer iteration 14): the contracts assembled and type-checked

Every code block in Contracts 01-08 was transcribed into a scratch package in
§ Project Structure's import order, with the smallest possible fill-ins where
a contract gives only a signature. mypy and ruff then ran under this repo's
settings. The assembly also ran the 53 specification examples (all agree),
every contract table row, and a 297-value round-trip corpus (267 round-trip
and are idempotent, 30 raise `UnrepresentableValueError`, and none fails).
Every error class survives `pickle` and `copy`. R-09 sanity: `k: "a" x`
strands at 7 of 8. R-02 sanity: `a\r\r\nb\r` has three breaks before and
after normalization, and `crlf_indices == (2,)`.

No Critical or High finding. Every defect below fails a gate (mypy, ruff,
or coverage) on the first commit that transcribes it. None gives a wrong
result at run time. That matches pass 12's rating of the same defect class
(`Root(...)` built without `level`).

- **Four contract code blocks fail the repo's mypy gate (Medium, Type
  Safety).** Found by running mypy, verified. (a) Contract 03
  `TextLeafNode.as_data` / `as_source` subtract `baseline: int | None`
  three times. The `inline` guard is a run-time argument, and mypy does
  not accept it. (b) Contract 03 `Mapping.add_node` reads `node.key` on a
  `SymlNode` and stores it in `dict[str, KeyValue]`, which gives two
  errors. (c) Contract 02's loop wrote `root = tip = Root(...)`, which types
  `tip` as `Root` and rejects `tip = tip.incorporate_node(...)`. (d)
  Contract 06's `load` narrowed `name` with `isinstance(name, (str,
  os.PathLike))`, which is not assignable to `StrPath | None`, and ruff
  `UP038` also rejects it. The obvious local fixes are the ones this plan
  forbids: `assert` (ruff `S101` in `src/`) and an unreachable guard (a
  pragma). **Mitigations**: (a) a `_base()` helper that returns `level`
  when `baseline` is `None`. (b) `cast('KeyValue', node)`, since an
  `isinstance` guard adds a branch nothing reaches. (c) `tip: SymlNode =
  root`. (d) `isinstance(name, str | Path)`, because `open(Path(p)).name`
  is a `str` (verified). With these, the assembly passes mypy with no
  errors. Under `--strict` (not this repo's setting) one more remains:
  `loads` returns the `Any` that `as_data()` is typed as (`warn_return_any`).
  It is recorded, not changed.
- **Principle VI missed three `Source`/`Pos` changes (Medium,
  Congruence).** Contract 08's change table has `Source.from_node` going
  from two arguments to four, `Pos.from_str_index` / `Source.from_text`
  counting `\n` only, and `Source.__add__`'s corrected `end`. Principle VI
  guards `Source`/`Pos` semantics, but none of the three was in the
  Constitution Check or the migration notes. All three are added above,
  with the rejected alternative, and to Contract 09 note 10. Note 12 now
  covers `SymlParser`'s new constructor.
- **Nothing said how the unreachable node stubs get covered (Medium).**
  The Principle III row allows only `TYPE_CHECKING` pragmas in `src/`.
  But today's `nodes.py` pragmas seven sites no input reaches: the
  abstract `as_data`/`as_source`, the base `can_add_node`, the base
  `incorporate_node`'s fail line, `KeyLeafNode.can_add_node`, and
  `Comment.as_data`/`can_add_node`. Contract 08's `rg` check looked at
  `nodes.py` only. The natural `incorporate_node` also ends in a bare
  `NoReturn` call, which fails ruff `RET503`. **Mitigation (Contract
  03)**: a disposition table. The last three sites are deleted and the
  first four get direct tests. `incorporate_node` ends in `return
  self.fail_to_incorporate_node(node, doc)`, and the `rg` check covers all
  of `src/`, `nobranch` included (Contract 08). `Source.from_text`'s
  `substring is None` pragma goes too.
- **Low.**
  - Contract 04's scan step said "an unescaped `"` ends the scan". That is
    the unreachable branch the next paragraph forbids. It now says a valid
    escape is skipped whole. No test obligation had a valid escape before
    the defect, so the skip was uncovered and `\"` untested. Two rows are
    added: `k: "a\"b` gives `escape=None`, and `k: "a\nb\x"` gives `\x`.
  - `QuotedStringDefect` fails ruff `N818`. It keeps its name with a
    reasoned `noqa`, because it never reaches a caller. Contract 06's
    `# noqa: F401` beside `__all__` was `RUF100` and is dropped.
  - `SymlData` written as a plain assignment raises `NameError` at import.
    mypy passes it and ruff `F821` catches it. It is now pinned as a PEP 695
    `type` statement (Contract 07).
  - The typed test module needs `# type: ignore[arg-type]` on `dumps(5)`,
    and `[dict-item]` (not `arg-type`) on literals such as `{1: 'v'}`. Under
    `warn_unused_ignores` those same ignores are the static half of
    "rejects `dict[int, str]`". Fake handles subclass `io.StringIO`
    (Contracts 06, 07).
  - `find_first` is pinned as an explicit-stack loop, which gives `-> Node`
    with no `raise` and no pragma (100% branch coverage, verified).
    `Mapping` must be `@dataclass(kw_only=True)` for its `keys` field
    (Contract 03).
- **Open item 4's neighbours (no new item).** Under §4.1 as printed:
  `- 'a:''` is `[{"'a": ""}]`; `- 'a:'b'` is `[{"'a": "b"}]`, while
  `k: 'a:'b'` raises trailing content; `- "k": v` is `[{'"k"': 'v'}]`.
  They are the same class as item 4 (`key` admits a quote, and `value`
  tries `structure` first). Either of item 4's grammar edits settles them
  too.
- Recursion figures re-measured under pytest with coverage: the inline limit
  is 118, the block limit 481, and `dumps` fails on nested lists at 951. The
  test obligations (50/200 inline, 400/500 block) and Contract 09's note 13
  hold.

### Pass 24 (2026-09-23, outer iteration 15): a data-model and coverage gap left by pass 23

Re-verified both named targets fresh rather than by citation. R-09: rebuilt
Contract 02's exact grammar in parsimonious and ran `GRAMMAR['line']` — `k: "a"
x` strands at index 7 of 8 and `- k: 'a'\tx` at 8 of 10, matching the claimed
anchors and confirming `parse()` raises `IncompleteParseError` at the same
point `match()` stops (no other partial-match cause found). R-02: `a\r\r\nb\r`
still splits into 3 breaks under the single-pass `\r\n|\r|\n` regex, both
before and after normalization. Checked pass 23's migration-note and
pass-log claims for follow-through, and read every older pass-log entry for
stale forms (`root = tip`, two-argument `from_node`, tuple-form `isinstance`)
— none found; the historical entries correctly describe what was true when
each was written, and the current-state contracts already reflect pass 23's
fixes.

- **`Pos.from_str_index`/`Source.from_text`'s `\n`-only counting was a
  Principle VI item with no data-model line (Medium, Congruence).** Pass 23
  added this as the third Source/Pos change (Contract 08's change table, plan
  migration note 10), but data-model.md §4 — which pass 23 did not touch —
  only mirrored the other two (`from_node`'s four-argument form, `__add__`'s
  `\n`). **Mitigation**: one sentence added to data-model.md §4.
- **`Source.from_text`'s `substring is None` pragma was named in the pass 23
  log but never landed in Contract 08 (Low, Congruence).** The log entry says
  "`Source.from_text`'s `substring is None` pragma goes too," but Contract
  08's Coverage section only discusses `nodes.py`'s `as_source` pragma, and
  the Hygiene/Test-obligations sections say nothing about `basetypes.py`.
  Verified against today's `src/syml/basetypes.py:71` that the pragma exists
  as described. **Mitigation**: Contract 08 now states the removal
  explicitly (§ Coverage) and adds a test obligation (a `from_text` call with
  no `substring`).

### Pass 25 (2026-09-23, outer iteration 15): the test obligations as one suite

Pass 23 ran coverage over tables and corpora; this pass ran it over the
**obligations**. The Contract 01-08 code blocks were rebuilt into a scratch
package (pass 23's assembly, unchanged in code by pass 24), with
`# pragma: no cover` on the `if TYPE_CHECKING:` lines only. Every "Test
obligations" bullet of Contracts 01-08 was then written as a pytest module
under plan.md's test-file names: 406 tests. They ran under this repo's
addopts (`--cov` with `branch = true`, `--random-order`, `--strict-markers`,
`--strict-config`) with five `--random-order-seed`s, and mypy ran over the
tests with this repo's settings. A throwaway pytest-bdd 8.1.0 project checked
the acceptance strategy against the installed parser. Sanity for the two
standing targets: `GRAMMAR['line'].match('k: "a" x').end == 7` of 8 (R-09),
and `a\r\r\nb\r` has `crlf_indices == (2,)` and three breaks (R-02).

No Critical or High finding. No obligation depends on test order. The
recursion obligations keep their margins (block 400/500 against 481, inline
50/200 against 118). Spec extraction finds 53 blocks under `**Output:**` and
54 under a looser `**Output …:**` match, with no mismatch either way.

- **The obligations alone do not reach 100% branch coverage (Medium,
  Coverage).** Verified. Four sites were left: `load`'s
  `if filename is None:` false arm (no obligation passes `filename` to
  `load`), `Source.from_text`'s `substring` arm, its no-match `raise
  ValueError`, and `Source.__repr__`. Today's `tests/test_basetypes.py` covers
  the last three, but by whole-`Source` `==`, which Contract 08 says must go,
  and nothing said to keep them. **Mitigation**: Contract 06 adds an
  explicit-`filename` obligation. Contract 08 adds the three `basetypes`
  obligations, keeps `Source + 5` → `TypeError`, pins
  `from_str_index`'s past-end clamp (the existing test's expected line
  becomes 7 under LF-only counting), and notes the `# type: ignore[index]`
  that `{src: 1}["foo"]` needs under mypy (verified).
- **A Contract 07 row contradicted rule D (Medium, Congruence).** The
  list-item table gave `a: b` as a mapping value as `k: 'a: b'`. Rule D
  exempts a mapping's inline value and no other rule applies, so a correct
  `dumps` emits `k: a: b`, which loads back as `{'k': 'a: b'}`. The row
  failed on the assembly. "Every row" was an obligation, so a worker would
  either write a failing test or make `dumps` over-quote to pass it.
  **Mitigation**: the row is corrected, and the table is now an explicit
  obligation.
- **`rg 'splitlines' src/` fails on the contracts' own code (Medium).**
  Contract 01's `split_lines_lf` docstring, Contract 05's `original_line`
  docstring, and Contract 08's `__add__` comment all name the method in order
  to forbid it. A verbatim transcription fails the check (verified).
  **Mitigation**: Contract 01 checks for a `.splitlines` call over the AST.
  That passes on the transcription and fails on a real call.
- **Worker guidance teaches the pragma the contracts forbid (Medium).**
  Constitution III's parenthetical, `CLAUDE.md` § Conventions, and the
  `pytest-unit-testing` skill all point to "the established pattern in
  `nodes.py` and `parsers.py`". The skill's worked example is
  `SymlNode.as_data` with `# pragma: nocover`, the exact stub Contract 03
  tests directly and the permanent `rg` test rejects. **Mitigation**:
  Contract 09 moves all three into the first commit. III keeps its
  permission and drops only the file pointer. This plan's Principle III row
  now says that the feature's rule is stricter.
- **Hand-off gaps a task generator would have had to guess (Medium).**
  (a) `utils.py`: "replaced" allowed either a rewrite or a deletion. Neither
  helper keeps a caller, so `utils.py` and `tests/test_utils.py` are
  deleted, `split_lines_lf` stays the one splitter, and migration note 16
  records it (Contracts 01, 09). (b) Contract 06 had no test file, so it
  now goes in `tests/test_api.py`. (c) US7's "shared corpus fixture" could
  not be shared: US7's binding is under the ignored `tests/acceptance/` and
  `test_serializer.py` cannot see a fixture from there. It is now the module
  `tests/serialization_corpus.py` (Contract 07). (d) The fixture decoder's
  "anything else raises" ran under no test, so it moves to
  `tests/fixture_escapes.py` with unit tests (Acceptance Test Strategy note
  1). (e) The ordering constraints were stated in three places and did not
  cover `todo.txt`'s deletion or the pragma guidance. They are now one list,
  Contract 09 § Leaf ordering.
- **Low.**
  - `Given a SYML document ""` cannot bind to US00's `parsers.parse` step
    pattern, and the failure is `StepDefinitionNotFoundError`, the RED
    marker. Verified. Note 1 now gives the `parsers.re` binding.
  - Contract 09: `CHANGELOG.md` is pinned, so US9.3's binding has one file
    to read. README's serializer section, which Contract 07 and R-06 cite,
    is now listed as a deliverable. `SYML-SPEC-REVIEW.md`'s title and
    subject already say "v1.0", so its required end state is now spelled
    out. Three more glossary entries go stale (Line node, Indentation
    level, `Pos`). Two skills name `todo.txt`. No template is affected.
  - Migration note 16 covers the node-tree internals reachable through
    `parse` (`level` semantics, `set_level`, the `doc` argument,
    `KeyLeafNode.key`) and `syml.utils`.
  - Contract 02 names `GRAMMAR_TEXT`, so the smoke test can recompile the
    shipped grammar under an error filter without `importlib.reload`. A
    reload would swap `GRAMMAR` under other tests in random order.
  - Tests that shell out trip ruff `S404`/`S603`/`S607`, and `tests/`
    ignores none of them. They take line-level `noqa`s (note 3).
  - Second-order check of the new obligations (same pass). Run against the
    assembly, `Source + 5` gave `AttributeError`, because Contract 08 showed
    only `__add__`'s `str` arm, and `from_str_index` had no clamp. Contract
    08 now shows the whole method and the clamp. With both, 411 tests pass
    at 100% line and branch coverage under three seeds. The shared helper
    modules also needed a pinned import form and a `pythonpath` entry
    (note 1).
  - `just acceptance` passes `-o addopts=""` and so drops
    `--strict-markers`. An unregistered `@feature-exit` there is a warning,
    not an error. Registration stays (Contract 09).

### Pass 26 (2026-09-23, outer iteration 16): hostile input, the old tests, and the 0.6.2 user

The pass 25 assembly was copied and attacked from outside: hostile input
sizes, Python 3.12, 3.13, and 3.14 (each with Parsimonious 0.10.0), today's
`tests/`, and 37 realistic documents run through both 0.6.2 and the
assembly. The fixes were then applied to a copy of the assembly and the
pass 25 suite re-run: 411 tests pass at 100% line and branch coverage under
three seeds, with mypy and ruff unchanged from pass 25. R-09 sanity:
`GRAMMAR['line'].match('k: "a" x').end` is 7 of 8. R-02 sanity:
`preprocess('a\r\r\nb\r')` has `crlf_indices == (2,)` and three breaks.

- **A valueless key in a list item changes silently (High, Migration).**
  R-11 measures a child against the key's own column, so `- server:\n
  host: x` is `[{'server': '', 'host': 'x'}]` in 1.0, where 0.6.2 gave
  `[{'server': {'host': 'x'}}]`, and nothing raises. With a list or text
  under the key (`- foo:\n  - bar`) it is `OutOfContextNodeError`. This
  follows §9.3 as printed ("strictly greater than a KeyValue's level"),
  but no migration note said it and no obligation pinned it. Two of
  today's tests assert the 0.6.2 reading. A worker who sees them go red
  with no guidance could "fix" `level` and undo R-11. **Mitigation**:
  Contract 03 gains the five-row table and a disposition for
  `tests/test_parsers.py`. Contract 09 gains note 17. Open item 7 asks the
  principal whether §9.3 means this. The plan implements §9.3 as printed.
- **`dumps` wrote a `(str, Enum)` member as `Color.RED` (High,
  Correctness).** An f-string renders a mixin member by its name on 3.12
  and later, so `dumps({'color': Color.RED})` gave `color: Color.RED`. That
  loads back unequal, and nothing raised. A subclass overriding `split`
  and `startswith` got `'- b'` through as a root scalar, which loads as
  `['b']`. **Mitigation (Contract 07)**: every key, value, and root scalar
  is read through `str.__str__(s)` before any rule sees it. Verified on
  the rebuilt assembly: `c: red`, `red: x`, `- red`, and `red` all round
  trip, and the `'- b'` subclass raises `UnrepresentableValueError`.
- **Silent value changes missing from the migration notes (Medium).**
  From the 37-document diff: `path: "C:\new\temp"` now decodes to a
  newline and a tab, `path: "C:\Users\me"` now raises, an indented root
  scalar keeps its indentation, CRLF values lose their trailing `\r`, and
  a leading U+FEFF no longer joins the first key. **Mitigation (Contract
  09)**: notes 4 and 7 are sharpened and note 18 is added. The note on
  traceability says why the audit-gap check cannot find these: they are
  side effects of fixes, not gaps.
- **Escape-dense quoted values still cost about 1 KB per character
  (Medium, Performance).** Pass 18 left `escape_seq` as printed. A 0.6 MB
  line of `a\n` pairs took 2.9 s and 565 MB, against 0.00 s and 28 MB in
  0.6.2. **Mitigation (Contract 02)**: each quoted body is now one regex
  atom that holds `escape_seq`'s alternatives. The equivalence was checked
  by brute force over 4,444,444 lines up to length 6, with 0 differences
  in match ends or named spans down to `quoted_value`. The same line now
  takes 0.06 s and 62 MB. Contracts 04 and 07 no longer name `escape_seq`
  as a grammar rule.
- **Nodes kept their parse nodes (Medium, Performance).** Nothing reads
  `pnode` after construction, and it was 36% of a parsed tree's retained
  memory. **Mitigation (Contract 03, data-model §3.1)**: the field is
  removed, and migration note 16 says so. On the rebuilt assembly a
  100,000-line document went from 5.0 s / 314 MB to 3.7 s / 218 MB (0.6.2
  took 24.6 s for a tenth of it).
- **Principle V misstated Parsimonious's engine, and the `regex` pin blocks
  Python 3.14 (Medium, Packaging).** `parsimonious/expressions.py` does
  `import regex as re`. On 3.14, `--only-binary` resolution of syml's
  `regex>=2024.11.6,<2025` fails. **Mitigation**: the Principle V bullet is
  corrected, since R-01's decision stands but its stated reason was wrong.
  research.md still carries that reason and is left for the principal.
  Contract 09 removes syml's direct `regex` line, and Parsimonious's own
  requirement, which has no cap, supplies it.
- **Low.** Note 13 now states how the recursion limits scale:
  block ≈ limit/2 and inline ≈ limit/8, the same on 3.12, 3.13, and 3.14.
  No crash was seen at a raised limit of 1,000,000 with 50,000 levels. It
  also states the memory cost an embedder should bound. A cyclic structure
  passed to `dumps` raises `RecursionError` (Contract 07). Every C0 and C1
  control, and the Unicode separators and spaces, round-trip at all five
  positions (3,440 cases, 0 failures). Nothing needed.

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
5. **Should a leading U+FEFF make a value unrepresentable instead?** Pass 14
   has `dumps` prepend a protective U+FEFF when the document would otherwise
   begin with one. Its output then starts with two marks, which no human
   would write. The alternative is to raise `UnrepresentableValueError` for a
   root scalar, or a first root-mapping key, that begins with U+FEFF. That
   adds a normative condition to §11.2.3/§11.2.4, so it is left for the
   principal.
6. **Should 1.0 change the `Development Status` classifier?** `pyproject.toml`
   says `4 - Beta`. FR-014 pins only `version`, so Contract 09 leaves the
   classifier unchanged. Moving to `5 - Production/Stable` is a release
   judgement, not a conformance question (pass 25).
7. **Does §9.3 mean a child at a list-item key's own column to be a
   sibling?** `- server:\n  host: x` is `[{'server': '', 'host': 'x'}]`
   under §9.3 as printed with R-11's own-column `level`. YAML and 0.6.2
   both nest it. No example in the specification shows a valueless inline
   key with block content, so the text decides it alone. The plan
   implements it as printed, pins it (Contract 03), and documents it as a
   silent change (Contract 09 note 17, pass 26). Nesting it instead would
   need a normative §9.3 edit, and it would add a special case to R-11.
8. **Should CI test more than Python 3.12?** `requires-python = ">=3.12"`
   is open-ended, and the design's figures were measured on 3.12, 3.13, and
   3.14 (pass 26). CI's matrix is `["3.12"]` only. Adding versions is a
   workflow change, and it may surface dev-group pins (`pytest-cov<6`,
   `ruff<0.7`, and others) that have nothing to do with conformance. So it
   is left as a release judgement, beside item 6.

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
