# Quickstart: syml 1.0 Spec Conformance

**Feature**: `001-syml-1-0-conformance` | **Epic**: `syml-x0m`

Orientation for whoever picks up implementation. Read `plan.md` first, then this.

## The shape of the work

Nine user stories, twenty functional requirements, twenty-one verified gaps.
They cluster into six layers, and the layers have a hard dependency order —
every layer below depends on the ones above it being right.

```
  1. Pre-processing    (§9.0)   FR-002, FR-003        US2   Contract 01
         │                        BOM, CRLF, tab scan, LF-only splitting,
         │                        PositionMap
         ▼
  2. Lexing            (§4.1)   FR-004                US3   Contract 02
         │                        grammar transcription, per-line entry point,
         │                        level = own column
         ▼
  3. Tree building     (§9.2-4) FR-005, FR-006, FR-007 US1, US4  Contract 03
         │                        ==-siblings, closed nodes, D11 baseline,
         │                        re-offer, duplicate keys, "" not None
         ▼
  4. Quoting           (§4.7)   FR-008                US6   Contract 04
         │                        decode, quote-guard post-check, completeness
         ▼
  5. API + errors      (§11)    FR-009..FR-011        US5, US7  Contracts 05-07
         │                        taxonomy, binary load, dumps/dump
         ▼
  6. Source + release  (§10,§14) FR-012..FR-020       US8, US9  Contracts 08-09
                                  original-text Pos, coverage, migration notes,
                                  constitution amendment
```

Layer 1 is first because its divergences contaminate every other layer's
results — a CRLF that survives normalization makes every value in the document
wrong, and the acceptance suite would be measuring the wrong thing.

## Running things

```sh
uv sync --all-groups
uv run pytest                # unit suite (deselects `acceptance`)
just acceptance              # pytest-bdd Gherkin suite
just acceptance-missing      # stub step definitions for unbound steps
just check                   # lint + type-check + test
./runtests.sh                # fast loop: ruff fix+format, pytest, mypy
```

The 100% coverage gate (`--cov-fail-under=100`) runs only in the pre-commit hook
and CI, not in `uv run pytest`. A green local run can still fail on commit.

## Non-obvious things that will bite you

1. **Fixtures with trailing whitespace cannot be file literals.** The
   `trailing-whitespace` pre-commit hook strips them from `.feature` files,
   `.py` files, and these planning documents alike. Every SYML fixture is a
   single-line escaped string; a significant trailing space is written `\x20`.
   Never use a `"""..."""` literal for a SYML document. (research.md R-05)

2. **`\x20` applies to the plan documents too.** A `key:` plus trailing space
   inside a fenced block in `plan.md` or a contract gets silently stripped at
   commit. These documents use `␠` (U+2420) as a visible marker.

3. **`tests/test_nodes.py.orig` is untracked and globally gitignored.** Git
   cannot see it. Read it and fold its content in — do not try to `git mv` it.
   (FR-017, Contract 08)

4. **Parsimonious evaluates `~"..."` bodies as Python string literals.** That is
   why `\s` in the grammar emits two `SyntaxWarning`s at import. The enumerated
   key class fixes conformance (D15) and the warning at once. (research.md R-01)

5. **`UnicodeDecodeError.start` is a byte offset**, not a code-point index. A
   fixture with a non-ASCII character before the bad byte is mandatory, or the
   off-by-N never shows. (research.md R-04, Contract 05)

6. **`str.splitlines()` is forbidden by §13.3, by name.** It recognizes U+2028,
   U+0085, U+000B, U+000C as line breaks. This is audit gap #16 and it must be
   fixed *before* the position-remapping work, not after. (Contract 01)

7. **`level` is the node's own column, not the line's indent.** `visit_line`'s
   `set_level(indent.level)` recursing into children is what makes
   `-   name: Alice` register column 0 instead of 4. (research.md R-11)

8. **The constitution amendment goes first.** FR-019 relaxes principle IV's
   "settle before implementing" clause. Until it lands, any commit that edits
   spec text alongside a behaviour change violates the constitution as written.
   (Contract 09)

## Settled — do not re-litigate

From the brainstorm's Key Decisions and `todo.txt`'s section (c):

- `todo.txt`'s A1 OPEN QUESTION is **decided**: trailing content after a closing
  quote is `MalformedQuotedStringError` (D2). Same for unterminated quotes and
  invalid escapes.
- D17 stands: no root-scalar quoting; `dumps` raises.
- All §13.4 limits are deferred past 1.0; `DocumentLimitError` is **not** one of
  the seven exported classes.
- Clean break from 0.6.2 — no 0.7 bridge, no compatibility flags.
- `dumps`/`dump` are in scope for 1.0.
- `EncodingError` is a `ParseError`.

research.md's "Carried forward from the brainstorm" table holds the full list
with each rejected alternative.

## Where to look things up

| Question | File |
| --- | --- |
| Why was X decided this way? | `research.md` (R-01..R-11) |
| What are the entity fields and invariants? | `data-model.md` |
| What exactly must this surface do? | `contracts/NN-*.md` |
| Which FR / user story / spec section? | every contract's header block |
| What does the spec actually say? | `SYML-SPECIFICATION.md` |
| Why does the spec say that? | `SYML-SPEC-REVIEW.md` (D1–D17, B/M findings) |
| What is currently broken, with a repro? | `specs/brainstorms/2026-09-14-*-audit.md` |
| Domain vocabulary | `docs/glossary.md` (four entries go stale — Contract 09) |
