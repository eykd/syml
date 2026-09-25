# Implementation Plan: SYML Language Revision — Values Are Just Text

**Branch**: `002-syml-language-revision` | **Date**: 2026-09-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-syml-language-revision/spec.md`
**Beads**: epic `syml-s9p9`, plan phase task `syml-s9p9.1`; findings epic `syml-xreq` (24 children, linked `related`)

> Fenced examples never carry a literal trailing space (the `trailing-whitespace`
> pre-commit hook strips them). Inputs are written as Python string literals
> (`'k:\n  a'`) wherever whitespace matters.

## Summary

Revise SYML 1.0 (unreleased) around one rule: **values are just text**.
Structure is decided at the first line of a block and at inline positions;
once a value is text, every later line at or past its baseline is that
value's text, blank lines between its lines are paragraph breaks, and `#`/`//`
mean nothing. Around that rule the feature tightens keys to
`[a-z][a-z0-9_-]*`, makes only U+0020 indentation, accepts a tab as separator
whitespace, rejects indentless sequences, gives errors a `file:line:col`
form with hints, lets `dumps` write everything the parser reads, and brings the
specification, decision record, changelog, and README into line before
tagging `1.0.0`.

The technical approach is small in code and large in text:

1. **One grammar swap** (Contract 01): adopt the spec's own
   `document = (line "\n")* line?` top rule so `indent` can be spaces-only,
   drop the `comment` rule, and narrow `key` and widen `ws`. Lexing stays
   per-line and context-free.
2. **Three tree-builder rules** (Contract 02), all riding on state the builder
   already has: the tip. A text tip re-reads any line at or past its threshold
   as text (R-01); paragraph breaks are counted from line positions when a
   continuation is attached (R-03); `Root` builds a root scalar from column 0
   (R-12). The indentless-sequence carve-out is deleted.
3. **Error text** (Contract 03): `ParseError.__str__`, a message naming the
   open columns read off `Root`'s rightmost spine, two hints, filenames on
   every error, and original-text positions from the tab scan.
4. **The serializer** (Contract 04) shrinks its refusal set to R-05's eight
   items, verified by a Hypothesis round trip with no excluded family.
5. **Release text** (Contract 06): spec first (principle IV), changelog,
   README, and the tag last.

## Technical Context

**Language/Version**: Python ≥ 3.12 (`requires-python = ">=3.12"`)
**Primary Dependencies**: `parsimonious>=0.10,<0.11` (runtime, unchanged).
`hypothesis` joins the `test` dependency group for the SC-002 round-trip
property (R-14); no runtime dependency is added.
**Storage**: N/A (in-memory parser)
**Testing**: pytest (random order; 100% branch coverage enforced at commit and
in CI), pytest-bdd acceptance via `just acceptance`, Hypothesis property tests
in the unit suite, mypy strict over `src/`, `tests/`, `tools/`, ruff preview
with pydocstyle.
**Target Platform**: library consumers on CPython 3.12+; PyPI (upload out of scope).
**Project Type**: library (`src/` layout, hatchling, `uv`).
**Performance Goals**: no regression beyond noise. The parse is still one
whole-document Parsimonious parse; the new work per line is O(1) (a level test
on the tip, a newline count over the gap since the previous line of the value).
Not an acceptance criterion.
**Constraints**: §13.4 limits stay unenforced (Scope Boundaries); the §9.2
walk-up stays recursive; the recursion cliff is measured and documented
(R-17). Version stays `1.0.0`; specification stays "Version 1.0" (FR-018).
**Scale/Scope**: ~1,330 lines of `src/`; every module touched, none added;
18 FRs; 4 user stories, 50 acceptance scenarios; 24 findings to close;
~60 specification examples to re-verify.

### Constraints carried from the brainstorm (Key Decisions)

- Values are just text (R3): position-based text context over per-line
  structural lexing, accepting one piece of reintroduced state (here: no
  builder-loop state; two new per-node fields, `content_pnode` and
  `line_pnode`, R-01).
- Strict indentation (R10): the spec as written over the YAML habit; the
  fixture is edited.
- Comments removed (R7): delete the feature rather than rule on its edges.
- ASCII keys with a leading letter (R1); non-ASCII keys are a knowing exclusion.
- Ship as 1.0.0 (R16): one breaking release, one spec version.
- Hints over new API (R12): message text only; no `reason` code or
  `expected_columns` attribute.

**No open clarification blocks planning.** The four deferred items are
settled in research.md R-01–R-05 (with R-04 settling a sub-question of item
c), and R-06–R-12 settle seven more questions that planning surfaced. The
distinct "Open Questions for the Principal" section below records verdicts
the red team reached on the planner's questions, two of which (7, 8) still
want the principal's confirmation before the spec leaf lands; neither blocks
drafting the plan.

## Brainstorm Context

**Source**: [specs/brainstorms/2026-09-24-syml-language-revision-requirements.md](../brainstorms/2026-09-24-syml-language-revision-requirements.md)

### Key Decisions Carried Forward

- Values are just text: once a value is text it is never reinterpreted
  (`syml-xreq.22`, option b generalized).
- Strict indentation, spec over YAML habit (`syml-xreq.3`).
- Comments deleted, not ruled on (`syml-xreq.21`).
- Key pattern `[a-z][a-z0-9_-]*` (`syml-xreq.16`, amended ruling).
- Ship as 1.0.0; the tag is the end state.
- Error improvements stay in the message string (`syml-xreq.18`).

### Deferred Questions (resolved during planning)

- How the builder carries "inside an open text value" → the tip is the state;
  `TextLeafNode.incorporate_node` re-reads a qualifying line as text (R-01).
- Adopting `document = (line "\n")* line?` so `indent` can be spaces-only →
  adopted as one atomic grammar leaf with blank classification in
  `visit_line` (R-02).
- Buffered or reconstructed blank lines → reconstructed from the normalized
  text's line breaks at attach time (R-03); an inline value's text counts as
  its first line (R-04).
- The residual unrepresentable set → eight items; FR-006 missed interior
  whitespace-only lines and later-line tab runs; one family with a spelling is
  still refused (R-05).

### Scope Boundaries (non-goals)

No new syntax (quoting, escapes, block-scalar indicators, document markers,
comments, empty-container tokens); no limit enforcement or
`DocumentLimitError`; no iterative walk-up; `Source` stays a non-`str` class;
`syml-xe9b.5`–`.7` excluded; no PyPI upload; Dependabot alert 8 untouched.

## Constitution Check

_GATE: evaluated before Phase 0 and re-checked after Phase 1. Constitution
v2.0.0 (amended 2026-09-23)._

| Principle | Pre-Phase 0 | Post-Phase 1 | Notes |
| --- | --- | --- | --- |
| I. Test-Driven Development | PASS | PASS | Every contract ends in test obligations; `sp:05-tasks` turns them into a beads Test List; RED commits via `.venv/bin/python -m tools.commit_red`. The spec-example oracle and the round-trip property are RED before the code leaves that satisfy them. |
| II. Type Safety | PASS | PASS | New fields are typed (`content_pnode: PNode \| None`, `blank_lines_before: int`); `ParseError`'s new keyword is `StrPath \| None`; the property tests are annotated (`-> None`, typed strategies). |
| III. Coverage and Lint Gates | PASS | PASS | No new pragma. Code made unreachable by the change is deleted, not exempted (Contract 03 on `SymlNode.fail_to_incorporate_node`; the D19 and comment paths). |
| IV. Spec vs Implementation Discipline | PASS | PASS | Every behaviour change cites an FR (FR-001–FR-018) and a new decision (D20–D25). The spec and review-document edits are the **first** leaf, so no code commit cites a decision that does not yet exist. The spec contradictions found in planning are settled here, not left for implementation (R-04, R-06, R-11). |
| V. Simplicity / YAGNI | PASS | PASS | Every leaf is still a plain `str`. **Lexing stays line-oriented and context-free**: each line lexes on its own characters; only the tree builder decides that an open text value absorbs it (R-01). No new runtime dependency; `hypothesis` is test-only (Complexity Tracking). Two classes, one visitor, and four helper functions are deleted. |
| VI. Public API Stability | PASS with declared breaks | PASS with declared breaks | Signatures of `loads`/`load` are unchanged. Behaviour breaks are listed below; all ship inside the 0.6.2 → 1.0.0 major bump, since 1.0.0 is not yet released. |

### Principle VI — declared changes on the guarded surface

| # | Change | FR | Non-breaking alternative rejected |
| --- | --- | --- | --- |
| 1 | The language itself: keys (D20), text context (D21), paragraph breaks (D22), no comments (D23), tab separator (D24), strict depth (D25). Documents valid under the 1.0 draft change value or start raising. | FR-001, -003, -004, -007, -008, -010 | Opt-in flags per rule. Rejected: 1.0 is unreleased, and a flag per rule is a second language to maintain. |
| 2 | `str(ParseError)` changes from the args tuple to `file:line:col: message` + line text; `DuplicateKeyError.message` becomes `Duplicate key '<key>'`. `.message`, `.position`, `.line_text`, `.args` layout kept. | FR-011, FR-016 | A new `format()` method leaving `str()` alone. Rejected: `str(e)` is what a traceback shows, which is the complaint in `syml-xreq.18`. |
| 3 | `TabIndentationError.position` moves to original-text coordinates (a bug fix against CHANGELOG 10/11's promise). | FR-013 | None: the old value was wrong. |
| 4 | `load()` on a closed handle raises `TypeError`, not `ValueError`; `loads(bytes)` raises a clear `TypeError`. | FR-017 | Let `ValueError` through. Rejected: `except ValueError` catches it as a parse error (`syml-xreq.13`). |
| 5 | `Pos.from_str_index` at end-of-text after a trailing `\n` reports the next line, column 0; a root scalar's `Source` starts at column 0 when indented. | FR-017, FR-005 | Keep the inconsistent fall-through. Rejected: line/column disagreed with the index. |
| 6 | `dumps('')` returns `''`; `dumps` accepts `Source`. | FR-017, FR-014 | Keep `'\n'`. Rejected: contradicted its own docstring and rule A. |

## Spec Conformance

`SYML-SPEC-REVIEW.md` was read in full. This feature closes **no** open
B-/M-finding of the 2026-09-13 review (all were resolved in 1.0); it
**supersedes** five decisions and re-closes or moots five findings, and it
closes all 24 break-test findings filed against 1.0 in `syml-xreq`.

**Decisions**: D5 → D24, D12 → D22, D13 → D21, D15 and D19 → D20 (superseded);
D25 restores §4.2 rule 5 and §9.3's KeyValue row over the code's undocumented
carve-out (commit `a22bdfa`); D11 (baseline), D14 (spaces-and-tabs leading
run), D16 (document top rule, now adopted in code), D6 (zero-length value), D7
(one error class for §8.1/§8.2), and D18 (no quoting) are affirmed and
constrain the design. **Findings**: M6 closed by D23, M20 by D22, M24 changed
by D21, M21 and B9 moot under D20/D23. The review's open v1.2 candidates:
candidate 4 (post-marker tab as error) is rejected by D24; candidates 1–3 stay
open. No open spec question in the review document is touched.

**Finding → contract → acceptance story** (the pinning map `/sp:05-tasks`
uses to wire each `syml-xreq` child to its task; see Ready-queue hazard):

| `syml-xreq` | Subject | Contract | Story |
| --- | --- | --- | --- |
| .1 | only U+0020 is indentation | 01 (+04 round trip) | US11 |
| .2 | root scalar keeps indentation | 02 (+04) | US10 |
| .3 | strict depth, indentless rejected | 02 (+03 hint, 06 text) | US11 |
| .4 | filename prefix on every error | 03 | US11 |
| .5 | tab-scan positions | 03 | US11 |
| .6 | BOM-led lines round-trip | 04 | US12 |
| .7 | §11.3 vs exports | 05 (+06) | US13 |
| .8 | CHANGELOG 10/12/13/16 | 06 | US13 |
| .9 | §4.1 grammar, §8.3 message | 01, 03, 06 | US13 |
| .10 | recursion cliff documented | 06 (R-17) | US13 |
| .11 | blank-document `Source` | 05 | — (unit) |
| .12 | `dumps('')` | 04 | US12 |
| .13 | input type guards | 05 | — (unit) |
| .14 | `os.PathLike` filename | 05 | — (unit) |
| .15 | paragraph breaks | 02, 04 | US10, US12 |
| .16 | key pattern | 01, 04 | US10, US12 |
| .17 | uppercase keys are text + hint | 01, 03, 06 | US10, US11 |
| .18 | `str(e)`, open columns, hints | 03 | US11 |
| .19 | tab as separator | 01 | US11 |
| .20 | `- key:` sibling column (keep) | 02 (pin), 06 (README) | US11, US13 |
| .21 | no comments | 01, 02, 04 | US10 |
| .22 | text context | 02, 04 | US10, US12 |
| .23 | `dumps` accepts `Source`; docs | 04, 05 | US12, US13 |
| .24 | README "Coming from YAML" | 06 | US13 |

All 24 repros were re-run on this branch at `3bda444` and still reproduce
(research.md R-15).

## Project Structure

### Documentation (this feature)

```text
specs/002-syml-language-revision/
├── plan.md              # this file
├── research.md          # R-01..R-17
├── data-model.md        # node, parser, exception, serializer changes
├── quickstart.md        # manual and suite verification
├── contracts/
│   ├── 01-grammar.md
│   ├── 02-tree-building.md
│   ├── 03-errors.md
│   ├── 04-serializer.md
│   ├── 05-api-tail.md
│   └── 06-release-text.md
├── reference/           # campaign evidence (README corrected for R-06)
├── checklists/
└── tasks.md             # /sp:05-tasks (not created here)
```

### Source Code (repository root)

```text
src/syml/
├── __init__.py          # loads/load type guards, PathLike filename (05)
├── basetypes.py         # Pos.from_str_index end-of-text fix; Source docstring (05)
├── exceptions.py        # ParseError filename kw, __str__, error_message('') (03)
├── nodes.py             # TextLeafNode text context + paragraph breaks, Root root-scalar + failure message,
│                        #   KeyValue carve-out removed, IndentNode/Comment/comments removed (02, 03)
├── parsers.py           # grammar swap, visit_document/visit_line, D19 + comment code removed (01)
├── preprocess.py        # PositionMap before tab scan, filename into scan (03)
└── serializer.py        # residual set, Source, dumps(''), key regex, structure match w/o preprocess (04)

tests/
├── fixtures/bar.syml             # lines 24, 36 re-indented (02, R-13)
├── fixtures/lane4/               # the four SC-004 documents (02)
├── test_roundtrip_property.py    # new: lane-1 probe as Hypothesis tests (04, R-14)
├── test_spec_examples.py         # new count + §4.1 grammar identity + §11.3 exports (01, 05, 06)
└── test_*.py                     # rewritten where they pinned D5/D12/D13/D19/comments/carve-out

tests/acceptance/
├── test_us10_text_values.py
├── test_us11_strict_structure_errors.py
├── test_us12_serializer_round_trip.py
└── test_us13_release_documents.py

specs/acceptance-specs/
├── US10-text-values.feature
├── US11-strict-structure-errors.feature
├── US12-serializer-round-trip.feature
└── US13-release-documents.feature

SYML-SPECIFICATION.md, SYML-SPEC-REVIEW.md, CHANGELOG.md, README.md, CLAUDE.md   # (06)
```

**Structure Decision**: single library, existing layout; no module added or
removed in `src/`. Acceptance files take the next free numbers (`US10`–`US13`)
because 001 owns `US00`–`US09` in both `specs/acceptance-specs/` and
`tests/acceptance/`; `US06` is free but reusing a retired number would confuse
`git log`.

## Leaf Ordering (for `/sp:05-tasks`)

Principle IV and R-02's atomicity fix the order; within a stage, leaves are
independent.

1. **Spec leaf** (Contract 06 §A, §B): `SYML-SPECIFICATION.md` and
   `SYML-SPEC-REVIEW.md` (D20–D25, supersession notes), fully revised before
   any code. To keep every commit green under the pre-commit `pytest` hook,
   the same leaf adds a `PENDING: dict[str, str]` table to
   `tests/test_spec_examples.py`, keyed by `(source, stated output)` (the spec
   repeats some inputs, so source alone is ambiguous), naming the FR
   that will make each changed example true; those examples run as
   `xfail(strict=True)`. Each later leaf deletes the entries it satisfies (a
   strict XPASS fails the run if it forgets), and the release leaf deletes the
   empty table. `MINIMUM_EXAMPLE_COUNT` moves to the new count here.
2. **Grammar leaf** (Contract 01), atomic: top rule, `indent`, `ws`, `key`,
   `eol` (written `~r"\Z"`, Security Considerations), comment removal, D19 removal, `IndentNode`/`Comment` removal, grammar
   identity test, and the rewrite of existing tests that pinned D5, D15, D19,
   or comments.
3. **Tree-builder leaves** (Contract 02), in order: strict depth + `bar.syml`
   (independent); root scalar; text context; paragraph breaks (needs text
   context).
4. **Error leaves** (Contract 03): `ParseError` filename/`__str__`; tab-scan
   positions; out-of-context message and hints (needs 3 for the new shapes).
5. **Serializer leaves** (Contract 04), after 2–3: key regex; structure match
   without pre-processing; residual set; `Source`; `dumps('')`; then the
   round-trip property test (lands RED on anything still missing), with the
   load-first property P8, the Hypothesis `gate`/`fuzz` profiles, `just fuzz`,
   and `.gitignore`'s `.hypothesis/` in the same leaf (Contract 04).
6. **API tail leaves** (Contract 05): independent of 2–5.
7. **Release leaf** (Contract 06 §C–§F), last: README, CHANGELOG (with R-17's
   measurement after 2), CLAUDE.md, tag after merge.

### Existing tests that invert (rewrite, do not delete)

- `specs/acceptance-specs/US03-line-lexing.feature`: `key:\tv` (now a
  mapping) and `key: \tv` (now `"v"`).
- `specs/acceptance-specs/US04-empty-values.feature`: "A comment-only document
  yields the empty string" (now the root scalar `"# just a comment"`).
- `specs/acceptance-specs/US07-serialization.feature` and
  `tests/serialization_corpus.py`: rows `contains_blank_line`,
  `block_line_begins_with_comment_marker`, `comment_marker_root_scalar`,
  `uppercase_key`, the key-rule and root-scalar-refusal scenarios.
- `specs/acceptance-specs/US09-release-readiness.feature`: CHANGELOG item
  assertions.
- `tests/test_parsers.py`, `tests/test_nodes.py`, `tests/test_serializer.py`,
  `tests/test_preprocess.py`, `tests/test_documents.py`, `tests/test_exceptions.py`:
  comment, D19 uppercase, tab-separator, indentless-sequence, `IndentNode`,
  message-text assertions (about 90 matching lines by a rough grep; 05-tasks
  greps for `comment`, `uppercase`, `Listen`, `IndentNode`, `\t`, `>=`,
  `Failed to incorporate`).

## Ready-queue Hazard (for `/sp:05-tasks`)

`br dep tree syml-s9p9 --direction up` returns all 24 `syml-xreq` children
(they are linked to the epic with `related` edges), so ralph's `prep.sh` would
offer each bare child as a ready leaf. `/sp:05-tasks` MUST, for each child,
either add a `blocks` dependency from the child on the task that pins it
(per the Spec Conformance table), or have that task close the child from
inside and keep `syml-xreq.*` out of the drain's candidate set. No bare
`syml-xreq` child may be claimable as a leaf. `syml-xreq.20` (ruled "keep, no
change") is pinned by a US11 scenario and a README leaf, not by code.

## Acceptance Test Strategy

> **ATDD Outer Loop**: each user story with acceptance scenarios gets a
> Gherkin file and pytest-bdd bindings, created by `sp:05-tasks`, run by
> `just acceptance`, and marked `acceptance`.

| User Story | Acceptance Spec File | Bindings | Scenarios |
| --- | --- | --- | --- |
| US1: Prose, dialogue, and headers are text | `specs/acceptance-specs/US10-text-values.feature` | `tests/acceptance/test_us10_text_values.py` | 18 |
| US2: Strict structure, honest whitespace, errors say why | `specs/acceptance-specs/US11-strict-structure-errors.feature` | `tests/acceptance/test_us11_strict_structure_errors.py` | 14 |
| US3: The serializer writes everything the parser reads | `specs/acceptance-specs/US12-serializer-round-trip.feature` | `tests/acceptance/test_us12_serializer_round_trip.py` | 10 |
| US4: Documents describe what ships; 1.0.0 tagged | `specs/acceptance-specs/US13-release-documents.feature` | `tests/acceptance/test_us13_release_documents.py` | 8 |

**Pipeline**: pytest-bdd via `just acceptance`. US4 scenario 7 (the tag on the
remote) can only pass after the release leaf; its binding is written in the
release leaf, not earlier. Where a scenario needs whitespace a Gherkin string
cannot hold literally, write `\t`, `\xa0`, `\ufeff`, `\r` escapes and decode
them in the step (the 001 bindings already do this).

## Spec Corrections Made in This Phase

Planning found places where the spec contradicted itself or the code base;
they are corrected in `spec.md` in the plan commit and recorded in its
Clarifications:

1. **US2 scenarios 9–11** used inputs that FR-003 and US1 scenario 16 make
   valid text (R-06). New inputs: `k:\n  a: 1\n b: 2` (→ `3:1:`, open columns
   0 and 2) and `a: 1\n- x`.
2. **FR-006** gains R-05's missing families: a whitespace-only (non-empty)
   line anywhere, and a tab in any line's leading whitespace.
3. **FR-010** names both same-column lists in `bar.syml` (lines 23–24 and
   35–36, R-13).
4. `reference/README.md`: `doc05c` and `doc05d` now load as text (R-06).
5. User Story 3's closing sentence ("the residual unrepresentable set is
   exactly the values that have no spelling at all") was deferred to the spec
   leaf by earlier passes; red team outer iteration 3 **applied it in
   `spec.md`** instead, because `/sp:05-tasks` binds acceptance scenarios from
   `spec.md` and must not inherit a sentence the code contradicts. R-05 found one family that keeps a spelling (`k: a: 1\n  b` for
   `{"k": "a: 1\nb"}`) and `dumps` still refuses it; rule D also refuses
   control characters that §4.6.1 lets `loads` read verbatim (red team,
   below). The rewording must name both load-only families.
6. FR-016's and US4 scenario 4's phrase "loud for third-party files with
   `#` lines" is false for a `#`/`//` line that is the first line of a
   document or of a block (it silently makes the document or block one
   string, see Edge Cases & Error Handling). First deferred to the spec leaf;
   **applied in `spec.md` in red team outer iteration 3** (US4 scenario 4
   would otherwise become a US13 Gherkin assertion that the CHANGELOG says
   "loud", which Contract 06 §C forbids).
7. **FR-004** said the kept blank sits "between two continuation lines," with
   blanks "before the first continuation line" inert — read literally, that
   makes the blank in `k: first\n\n  second` inert, the opposite of R-04's
   verdict (`{"k": "first\n\nsecond"}`), because `first` is the inline value's
   text, not a continuation line, and `second` is the first one (deepen-plan
   pass, red team iteration 2 target). FR-004 now reads "between two lines of
   the same value," states that an inline value's text counts as the value's
   first line, and carries the R-04 example inline; Contract 02's rule 4 and
   Contract 06 §5.1 rule 5 already used this wording, so this closes the gap
   between them and the FR text rather than opening a new one.
8. **FR-006** (red team outer iteration 3) gains the recursion refusal: a
   later line of a multi-line value whose per-line lex exceeds the parser's
   recursion depth (Edge Cases & Error Handling, "A `- ` chain is text but
   still recurses"). FR-006's list was exhaustive ("MUST shrink to"), so the
   serializer could not refuse this family without the FR saying so.

## Open Questions for the Principal

The red team (pass 1) returned a verdict on each of the planner's questions;
the principal may still overrule any. Question 7 is new and is the one that
most deserves the principal's eye, because it corrects a fact a ruling rested
on. Question 8 was added by red team outer iteration 2.

1. **Silent absorption (R-06, D21).** `parent:\n  child1: a\n   child2: b`
   now loads `child2: b` as part of `child1`'s value instead of raising.
   **Verdict: keep.** No parser-side mitigation exists that does not
   contradict the ruling on `syml-xreq.22` and US1 scenario 16; the cost is
   recorded in D21's breaking-change note and the CHANGELOG D21 item, not the
   README list (FR-015 fixes it at eight items). The tab-separator variant of
   the same hazard is in Edge Cases & Error Handling.
2. **Inline-value blank line (R-04).** `k: first\n\n  second` keeps the blank
   (`"first\n\nsecond"`), reading FR-004's "continuation lines" as "lines of
   the value". **Verdict: keep** (consistent with the root case and needs no
   special case).
3. **One refused family with a spelling (R-05).** `{"k": "a: 1\nb"}` could be
   written `k: a: 1\n  b` but `dumps` refuses it, per FR-006; US3's narrative
   says "exactly the values that have no spelling at all". **Verdict: the
   narrative moves, FR-006 stands.** Accepting the family later is additive
   (non-breaking in 1.x); refusing it later would be breaking. The
   inline-first layout has its own baseline restriction the spike already
   tripped on (`{"a": "k: \n a"}`), and it makes the layout depend on the
   value's shape. The load-then-dump gap this leaves is pinned, not hidden:
   Contract 04's P8 property allows exactly two load-only families (this one
   and rule D's control characters) and fails on any third.
4. **`k: \tv` changes value (R-11, D24).** The ruling said nothing valid
   changes meaning; this one does (`"\tv"` → `"v"`). **Verdict: keep**,
   recorded in D24.
5. **Constitution IV's decision range.** It still reads "D1–D17" (D18/D19 were
   cited without amending it). Every change here also cites an FR, so the gate
   passes; the release leaf could PATCH the range to "D-numbered decisions"
   alongside CLAUDE.md's "D1–D25". Suggested, not planned.
6. **Closed-handle `TypeError` (R-10).** The spec's Edge Cases ask for
   `TypeError`; an `OSError` subclass would also escape `except ValueError`.
   **Verdict: keep `TypeError`** (the spec asks for it; either escapes
   `except ParseError`).
7. **"Loud" was the premise of the comments ruling, and it is false for the
   common case (new, red team).** The ruling on `syml-xreq.21` records
   "Consequences (all loud)". Under D21 a `#`/`//` line is loud only when it
   sits at a container's level *after* that container's first entry. When it
   is the **first line of the document** (a file header comment) the whole
   document silently loads as one `str`; when it is the **first line of a
   block** (`a:\n  # section\n  b: 1`) the whole block silently loads as one
   string (`{"a": "# section\nb: 1"}`). The same is true of a leading `---`,
   a leading uppercase or dotted would-be key (`Name: app`), and any other
   text first line. Nothing raises; a consumer fails later on `data["x"]`.
   **Plan position: the parser ruling stands** (changing it would reopen
   D21), and the release text is corrected (Contract 06 §A, §B, §C, §D).
   **Ask the principal** to confirm D23 with the corrected consequence before
   the spec leaf lands, since the tag makes it a 1.0 promise.

8. **No hint for a former comment line (new, red team outer iteration 2).**
   A 0.6.2 user's `a: 1\n# note\nb: 2` now raises "Line 2, at column 0, is
   a text line, but the open block at column 0 holds keys", with nothing
   saying that `#` stopped being a comment. FR-012 lists exactly two hints
   (the brainstorm's R12 list, minus the moot tab hint). A third hint, `Hint:
   SYML has no comments; a '#' or '//' line is text.`, on a failing line whose
   content starts with `#` or `//`, would be message text only, with no API.
   **Plan position: not added** (the CHANGELOG D23 item carries the warning,
   and the principal owns nothing with comment lines). **Ask the principal**
   whether third-party migration justifies it; adding it later is non-breaking.

## Security Considerations

`syml` parses documents that may come from third parties. Red team pass 1
(`.specify/solutions/` holds no prior security or clean-architecture entries,
so no carried-over finding applies).

### Input Validation: the grammar must load under the repository's warning policy

- `pyproject.toml` sets `filterwarnings = ["error::SyntaxWarning"]`.
  Parsimonious evaluates rule literals as Python string literals, so the
  `eol = &"\n" / ~"\Z"` rule that Contract 01 and research.md R-02 printed
  before this pass (and that the current §4.1 still prints) emits `SyntaxWarning: invalid escape sequence '\Z'`
  while `Grammar(...)` is built. Under the repository's policy that is an
  exception at `SymlParser`'s class body, so `import syml` fails and every
  test errors (verified: the planning spike does not import under
  `python -W error::SyntaxWarning`). The rule is written `~r"\Z"` in the code,
  in Contract 01, and in the §4.1 block the spec leaf prints; `as_rule()` is
  the same for both spellings, so the grammar-identity test is unaffected.
  The identity test loads §4.1's block under the same warning policy, so a
  future non-raw escape in the printed grammar fails it too.

### Data Protection: error text is rendered, not echoed

- FR-011 makes `str(ParseError)` print the offending line. In 1.0, `str(e)`
  was the args tuple, whose `repr` escaped control characters; the new form
  would copy an attacker's raw bytes (ANSI escape sequences, `\x07`, bidi
  overrides such as U+202E, NUL) into a terminal or log line. `__str__`
  therefore renders the line text and the would-be key in hint (a) with every
  character for which `str.isprintable()` is false (this includes a tab;
  U+0020 is printable and stays) replaced by its Python escape
  (`\t`, `\x1b`, `\xa0`, `\u202e`). `.line_text`, `.message`, and `.args` stay
  raw, so programmatic callers lose nothing. This also helps the whitespace
  errors this feature adds: `k:\n  a\n\xa0\n  b` shows `\xa0` on the second
  line instead of an invisible character (Contract 03).
- **The filename is rendered too (red team outer iteration 3).** The
  `<filename>:` prefix of `str(e)`'s first line is also caller- or
  attacker-controlled: an archive entry named `a\n.syml` splits `str(e)` into
  three lines (breaking Contract 03 obligation 8's two-line shape and forging a
  log line), `\x1b[2J.syml` is terminal-escape injection, and `load()` on a
  handle whose `.name` is an undecodable `bytes` path gives a filename with
  lone surrogates (`os.fsdecode(b'\xff.syml') == '\udcff.syml'`), so
  `print(e)` to a UTF-8 stream raises `UnicodeEncodeError` inside the
  caller's `except` block. `__str__` passes the filename through the same
  `_printable` helper as the line text. `.message` keeps the raw filename
  (like `.line_text`, a programmatic field). `ParseError` normalizes a
  `PathLike` filename with `os.fspath` in its constructor, so
  `loads(text, filename=PurePath("p.syml"))` and `load()`'s `.name` path give
  the same prefix (Contract 03, Contract 05).

### Resource Limits

- Unchanged by this feature: no limit is enforced (Scope Boundaries). The new
  per-line work is O(1) plus an O(gap) newline count per continuation, and the
  failure path's "previous non-blank line" scan is O(n) once per raised error,
  so no new super-linear path is added. The recursion cliff is measured after
  the grammar leaf (R-17).
- **One existing recursion path becomes reachable from text, and from
  `dumps` output** (red team outer iteration 3; Edge Cases & Error Handling).
  A long `- - - …` chain recurses in the per-line lex even where D21 makes
  the line text. The load side stays documented, not fixed; the serializer
  refuses to write such a line (FR-006, Contract 04 item 2).

## Edge Cases & Error Handling

### Silent cases the release text must name (red team pass 1)

Verified against the planning spike; each follows from the rulings and is
kept, but no document may call it loud:

| Input | Result | Why silent |
| --- | --- | --- |
| `# Application config\nname: app\nport: 80` | the `str` `"# Application config\nname: app\nport: 80"` | the first line is text, so the root is text throughout (D21, D23) |
| `a:\n  # section\n  b: 1\n  c: 2` | `{"a": "# section\nb: 1\nc: 2"}` | the block's first line is text (D21, D23) |
| `Name: app\nport: 80`, `---\nname: app` | one `str` each | same, via D20 and the no-document-markers rule |
| `-\tk: v\n        j: w` | `[{"k": "v\nj: w"}]` | a tab after `-` counts as **one** column, so `k` is at column 2 and a line an editor shows aligned under `k` (tab stop 8) is past it and joins the inline value (D24 × §6.2 × D21) |
| `parent:\n  child1: a\n   child2: b` | `{"parent": {"child1": "a\nchild2: b"}}` | R-06 |
| `name:\xa0app\nport: 80` | the `str` `"name:\xa0app\nport: 80"` | a NBSP (or any character other than space or tab) after `key:` is not separator whitespace (D24), so the line is text; as a first line it makes the root (or block) text. In 1.0 this raised at line 2; it is now silent (red team outer iteration 3; macOS Option-Space and pasted web text produce it) |

Consequences for the text leaves (Contract 06): D23's breaking-change note,
the CHANGELOG D23 item, and README "Coming from YAML" item 1 state that a
`#`/`//` first line of a document or block makes that document or block one
string, and that a later `#` line at a container's level raises; the
"loud for third-party files" wording is replaced. D24's note and §6.2/§7.5
state that columns are code-point counts, so a tab counts as one column. The
README list stays at eight items in order (FR-015); the silent cases go into
the wording of items 1, 3, 6, and 7, not a ninth item.

### Error text for prose values (red team outer iteration 2)

The out-of-context message was designed around structure, but under D21 the
commonest error a prose author hits is a line one or two columns short of a
text value's baseline. Two gaps, both fixed in Contract 03 and FR-012:

- **The open text value's column was missing.** `{COLS}` lists only the
  `List`/`Mapping` levels on the spine, so `k: a\n    b\n  c` (US1-18) said
  "open blocks are at column 0" and never mentioned column 4, where the value
  continues; US2-7's NBSP line likewise never named column 2. FR-012 asks for
  "every column that was open during the walk-up", and the walk-up starts at
  that value. The message now ends `; the open value continues at column {B}.`
  when the spine ends in a text value with a fixed baseline and the line is
  below it. An inline value with no continuation yet gets no clause, so
  US2-9's exact `str(e)` is unchanged.
- **Hint (a) named the wrong fix for dialogue.** An interactive-fiction value
  is full of `Name: line` text. In `- scene:\n    Bob: hi\n    Carol: yo\n   Alice: hey`
  the ungated hint says `'Alice' is not a key`; lowercasing it changes
  nothing, because the real fault is the one-space dedent. Hint (a) now
  fires only where a key could fit: the failing line at an open `Mapping`
  column (US1-8's `firstName` still qualifies), or the line above when it is
  the first line of the open text value (the line whose text-ness opened the
  context, `config:\n  Host: x\n port: 1`), never a later continuation.

Neither change adds API: both stay in the message string (the ruling on
`syml-xreq.18`). The planning spike never implemented the message (it still
raises `'Failed to incorporate a node'`), so these rows are pinned by
Contract 03's table rather than by spike evidence.

### A `- ` chain is text but still recurses (red team outer iteration 3)

D21 says a line inside an open text value is text "whatever it lexes as", but
lexing still happens first, per line, on the whole line. The grammar's only
recursive path is `value_list_item = "-" ws value` with
`value = structure / data`, so a line of `- ` repeated N times recurses about
N levels deep in Parsimonious before the tree builder ever sees it. On the
planning spike (called directly, default recursion limit) a line with a
little over a hundred `- ` repetitions raises `RecursionError` from `loads`
at any position: first line, continuation of a block value
(`k:\n  a\n  - - - … x`), or continuation of a root scalar. The exact depth
depends on the caller's stack and is R-17's to measure, not a promise.

- **Load side: documented, not fixed.** Scope Boundaries keep limits and the
  recursion cliff out of this feature. CHANGELOG item 13 and §13.4 name this
  shape alongside the nesting cliff (Contract 06 §C, measurement 5): a line
  made of many `- ` markers raises `RecursionError` even inside a text value.
  The alternative (an iterative `("-" ws)+` list-marker rule in the grammar,
  which would make text lines immune) was not taken here: it rewrites the
  grammar's list rules and visitor late in planning and moves the structural
  cliff rather than removing it. It is a 1.x candidate recorded in D21's note.
- **Serializer side: refused.** Before this feature `dumps` refused every
  structure-shaped later line (D13), so it never wrote such a line. Under
  R-05's "later lines are unrestricted" it would write
  `{"k": "a\n" + "- " * 400 + "x"}` and `loads` of the output raises
  `RecursionError`, an out-of-contract exception that breaks SC-002 and
  §11.2.1's "MUST raise rather than emit text that would not read back". The
  generated SC-002 inputs never reach that depth, so the property alone would
  not catch it. Fix: Contract 04 item 2 extends its existing
  `RecursionError`-counts-as-structure rule (obligation 4) from the first
  line to every later line of a multi-line value that begins with `-` after
  its leading spaces; such a line is refused with `UnrepresentableValueError`
  (FR-006). The check parses the line with the full `document` rule, so it
  recurses at least as deep as `loads` will; a pinned example uses a depth
  far past the cliff (several hundred) so it does not sit on the
  stack-dependent boundary.
- **P8's family predicate is `RecursionError`-safe.** A mapping value whose
  first line is a long `- ` chain loads fine (a mapping's inline value is
  `data`, §7.2) and is family L1; the predicate that recognizes L1 uses the
  same helper, so it classifies the line as structure instead of raising.

### Smaller notes (red team outer iteration 2)

- **NBSP-led first line is silent too.** `\xa0\xa0name: app\nport: 80`
  (indentation pasted from a web page) is a root scalar with no error, by
  FR-009 and D21. It belongs to the same family as the silent `#` first line.
  The CHANGELOG's only-U+0020-is-indentation item (Contract 06 §C) should name
  that consequence ("a document or block whose first line starts with a
  non-breaking space is one string"); no ninth README item is needed. Later
  NBSP-led lines raise, and `str(e)` shows `\xa0`.
- **The spike's `check.py` is stale on three rows.** It still expects
  `OutOfContextNodeError` for `k:\n  a: 1\n   b: 2`, `a: 1\n  - x`, and
  `parent:\n  child1: value\n   child2: value`, which R-06 made valid text.
  `/sp:05-tasks` takes expected values from spec.md and the contracts, never
  from the spike's scripts.
- **P8 holds on the spike.** A 20,000-example load-first run (documents
  built from indentation, markers, `K:`, `#`, `//`, NBSP, BOM, VT, and tabs)
  found no value outside families L1 and L2 that `dumps` refuses, and no
  round-trip failure, so Contract 04's P8 should land GREEN rather than
  surface a third family during implementation.

### Load-then-dump

US3's persona loads a file and writes it back. Apart from values `loads`
cannot return at all (the `- ` chain above raises `RecursionError` before
`dumps` sees it), `dumps` refuses exactly two families of values that `loads`
can return: a multi-line mapping value whose
first line is structure-shaped (R-05; `k: note: the door\n  is locked`,
`notes: - milk\n  - eggs`), and a value containing a control character that
§4.6.1 reads verbatim but rule D refuses (`\x0bx`, `a\x1cb`). Both stay refused
(open question 3). A load-first property (Contract 04, P8) pins them: for
generated documents that load, `dumps` either round-trips the result or raises
`UnrepresentableValueError` for a value in one of these two families, so any
third load-only family fails the suite.

## Performance Considerations

### Test-gate cost and determinism (Hypothesis)

- The pre-commit hook runs the whole unit suite under coverage on every
  commit. Hypothesis's default 200 ms `deadline` flakes under coverage
  instrumentation, and a random run that finds a new counterexample would
  block an unrelated commit. `tests/conftest.py` registers a settings profile
  with `deadline=None` and `derandomize=True` for the gate (loaded by
  default), and a `fuzz` profile (random, more examples) selected with
  `HYPOTHESIS_PROFILE=fuzz` for hardening runs; a `just fuzz` recipe runs it.
- `.hypothesis/` joins `.gitignore` in the same leaf that adds the property
  tests, because `/sp-commit` stages every change and would otherwise commit
  the example database.
- 100% branch coverage of `src/` must be reachable from the example tables
  alone; no branch may be covered only by generated inputs, or coverage would
  depend on the Hypothesis seed.

## Accessibility Requirements

Not applicable: `syml` is a library with no user interface. The only
human-facing output is error text, covered above (escaped rendering, a
`file:line:col` first line).

## Complexity Tracking

| Addition | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| `hypothesis` in the `test` dependency group (not runtime) | SC-002 requires the round-trip property over generated inputs with no excluded family; the campaign's lane-1 probe is already Hypothesis. | Hand-enumerated example tables cannot show "no excluded input family"; the probe found `syml-xreq.1` and `.6` only by generation. |
