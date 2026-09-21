# Contract 09 — Release text, migration notes, and the conformance ledger

**Requirements**: FR-014, FR-015, FR-016, FR-017, FR-018, FR-019, FR-020
**User story**: US9 | **Spec**: §11.3, §13.4, §14, §15

This contract has no Python surface. Its "signatures" are the exact file states
the feature must leave behind, each independently assertable.

## FR-014 — release text

| Artifact | Required end state | Assertion |
| --- | --- | --- |
| `pyproject.toml` | `version = "1.0.0"` | US9.1 |
| `SYML-SPECIFICATION.md` header | labelled **Version 1.0**; status line names `syml` 1.0.0 as the conforming reference implementation | US9.2 |
| `SYML-SPECIFICATION.md` §14 | the 1.1 and 1.0 rows folded into **one** 1.0 entry | US9.2 |
| `SYML-SPECIFICATION.md` §15 | the "As of ..." status line updated | US9.2 |
| `SYML-SPEC-REVIEW.md` | subject line updated to match | FR-014 |

## Spec edits this feature makes (FR-019's licence in use)

Each lands in the same commit as the behaviour it describes.

| Section | Edit | Driver |
| --- | --- | --- |
| §11.3 | add `EncodingError(ParseError)` | FR-009, R-04 |
| §11.3 | mark `DocumentLimitError` **post-1.0** | spec Edge Cases |
| §13.4 | mark the limits **post-1.0**; record the `RecursionError` as a known limitation | spec Edge Cases |
| §4.5 | one clarifying sentence: the C0 exclusion decides U+001C–U+001F, so the `White_Space` and `\x00-\x1f` clauses overlap there | R-01 |
| §14, §15, header | relabel to 1.0 | FR-014 |

Anything beyond this list is a red-team / implementation discovery and must be
recorded with its driving behaviour, per FR-019.

## FR-015 — migration notes

Location: `CHANGELOG.md` (created if absent) **or** README. Must list every
user-visible change from 0.6.2 (US9.3, SC-006):

1. Absent values: `None` → `""`, at every depth
2. Tabs in indentation → `TabIndentationError`
3. Duplicate keys → `DuplicateKeyError`
4. Quoted inline values now decode — and an apostrophe-initial inline value
   (`key: 'Tis`) is now `MalformedQuotedStringError`
5. `-` / `key:value` fallthrough: bare `-` takes a block value; `key:value` is a
   scalar instead of raising
6. Sibling indentation is now exact (`==`), and a closed key/item accepts nothing
7. Multiline values preserve indentation past the baseline; a below-baseline
   line terminates the value
8. Parsimonious exceptions no longer escape; everything is a `ParseError`
9. `ParseError` gains `.message` / `.position` / `.line_text`
10. `Pos` coordinates now refer to the **original** text
11. `load()` accepts binary streams; invalid UTF-8 → `EncodingError`
12. New: `dumps`, `dump`
13. Known limitation: nesting past ~500 levels raises `RecursionError`

The traceability check is mechanical: every row of the audit's gap list (b)
maps to a numbered entry here or is explicitly out of scope.

## FR-016 — one conformance ledger

| Artifact | End state | Assertion |
| --- | --- | --- |
| `todo.txt` | retired (deleted) or rewritten as a post-1.0 backlog holding **no** conformance claims | US9.4, SC-007 |
| `CLAUDE.md` § "Spec vs. implementation" | rewritten to state the parser conforms; the "do not assume the parser matches the spec" guidance removed | US9.4 |
| `docs/glossary.md` | four entries refreshed — see below | |

Recommendation: **delete** `todo.txt`. The audit's section (c) shows it is
superseded or reversed on A1, A3, A4, A9, A10, and section E; what survives
(B3) is FR-017. A rewritten file would carry no live conformance claim, which
makes it a backlog under a misleading name.

### Glossary entries going stale (flagged during planning)

| Entry | Why it goes stale |
| --- | --- |
| `incorporate_node` | described as climbing "by indentation level"; §9.2 climbs by **acceptance**, and level is now the node's own column (R-11) |
| `can_add_node` | described as "the per-node predicate a **container** implements"; `TextLeafNode` and `Mapping` now carry real logic (baseline, duplicate keys) |
| `TextLeafNode` | described as "accepts further `TextLeafNode`s as children" with no conditions; it now carries `anchor_level`, `baseline`, and `quoted` and declines more than it accepts |
| `OutOfContextNodeError` | "listed in `unwrapped_exceptions` so Parsimonious does not wrap it" — with per-line lexing (R-09) and a full wrapping boundary, that sentence describes an implementation detail that changes |

Add: `PositionMap`, `EncodingError`, `dumps`/`dump`, `Document` (original vs
normalized).

## FR-017 — hygiene

| Item | End state | Assertion |
| --- | --- | --- |
| `tests/test_nodes.py` | real tests; the untracked `.orig` folded in or deleted | US9.6 |
| `basetypes.Source.__add__` | dead `return` removed | US9.6 |
| `import syml` | no warning (`python -W error -c "import syml"`) | US9.5, SC-007 |

The `.orig` file is untracked **and** globally gitignored (`*.orig`). The task
must read it, not move it.

## FR-018 — release-ready, not released

No `1.0.0` git tag; no distribution built or uploaded (US9.9). Publishing is a
manual step after merge.

## FR-019 — constitution amendment

Amend principle IV and bump the constitution version per its own Governance
Amendment Procedure and Versioning Policy (US9.7). Required changes:

1. Drop "is aspirational and was written ahead of the implementation; it does
   not describe current parser behavior" — false once FR-014 lands.
2. Drop "`todo.txt` is the empirically verified conformance ledger" — false once
   FR-016 lands.
3. Relax "An open spec question ... MUST be settled (recorded as a decision)
   before implementing against it" to permit a specification edit landing in the
   **same commit** as the behaviour change that exposed it.
4. Keep the citation duty (every behaviour change cites a decision record). With
   `todo.txt` retired, citations point at D1–D17 and at this feature's FR-NNN.

**Version bump**: **2.0.0** (MAJOR). The constitution's own Versioning Policy
says MAJOR is for "backward-incompatible principle removals or **redefinitions**".
Change (3) flips a MUST, and changes (1)–(2) remove the factual premise the
whole principle rested on. That is a redefinition, not "materially expanded
guidance" (MINOR). Commit message per the Amendment Procedure:
`docs: amend constitution to v2.0.0 (principle IV: spec conforms; spec open during implementation)`.

**Sequencing**: the amendment is the **first** implementation commit, before any
behaviour change that also edits spec text — otherwise that commit violates
principle IV as currently written.

Also required by the Amendment Procedure: identify affected templates
(`.specify/templates/*`) and update `CLAUDE.md` (which FR-016 already touches).

## FR-020 — Constitution Check

Lives in `plan.md`, not here. See plan.md § "Constitution Check" (US9.8).

## Test obligations

US9's nine scenarios are **repository-inspection** steps, not parser tests. They
bind against file contents, `importlib.metadata.version('syml')`, and
`git tag --list`. Keep them in the acceptance suite (`just acceptance`), where a
non-parser Given/When/Then reads naturally, rather than in the unit run.
