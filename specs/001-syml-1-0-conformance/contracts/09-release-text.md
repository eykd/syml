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
| `SYML-SPEC-REVIEW.md` | title and `**Subject:**` line say the reviewed text was the pre-release draft (labelled v1.0 when reviewed) and that the text released as 1.0 incorporates these findings. Both lines already read "v1.0" today, so "updated to match" is not a no-op: after the relabel two different texts would carry that label (pass 25) | FR-014 |
| `README.md` | gains a serializer section (`dumps`/`dump`, the R-06 format choices Contract 07 points at, the `encoding='utf-8'` advice) and a link to `CHANGELOG.md`. Contract 07 and R-06 cite "the README's serializer section", which the 48-line README does not have (pass 25) | FR-011, FR-015 |
| `pyproject.toml` classifiers | unchanged (`Development Status :: 4 - Beta`) unless the principal decides otherwise (plan.md open item 6, pass 25) | — |
| `pyproject.toml` `dependencies` | `parsimonious>=0.10.0,<0.11` only. The direct `regex>=2024.11.6,<2025` line is removed. `src/` never imports `regex`. Parsimonious 0.10.0 requires it (`regex>=2022.3.15`, no upper bound) and compiles every grammar atom with it. syml's own `<2025` cap is what blocks Python 3.14: no `regex` release below 2025 has a 3.14 wheel, so `uv pip install --only-binary :all: 'regex>=2024.11.6,<2025'` is unsatisfiable on 3.14, while `requires-python = ">=3.12"` claims 3.14 (verified, pass 26). `uv.lock` is regenerated in the same commit (pre-commit's `uv-lock` hook) | `python -c "import syml"` on a Python 3.14 environment built from wheels only |

## Spec edits this feature makes (FR-019's licence in use)

Each lands in the same commit as the behaviour it describes.

| Section | Edit | Driver |
| --- | --- | --- |
| §11.3 | add `EncodingError(ParseError)` | FR-009, R-04 |
| §11.3 | mark `DocumentLimitError` **post-1.0** | spec Edge Cases |
| §13.4 | mark the limits **post-1.0**; record the `RecursionError` as a known limitation | spec Edge Cases |
| §4.5 | one clarifying sentence: the C0 exclusion decides U+001C–U+001F, so the `White_Space` and `\x00-\x1f` clauses overlap there | R-01 |
| §11.2.3 | one clarifying sentence: a key is unrepresentable whenever `key`'s class (§4.5) does not match all of it, which adds C0/C1 controls to the listed whitespace, `:`, and empty-key cases | FR-011, red-team pass 14 |
| §14, §15, header | relabel to 1.0 | FR-014 |

Anything beyond this list is a red-team / implementation discovery and must be
recorded with its driving behaviour, per FR-019.

## FR-015 — migration notes

Location: **`CHANGELOG.md`** (new), under a `1.0.0` heading. The earlier
"`CHANGELOG.md` or README" left US9.3's binding without a file to read
(pass 25); README links to it instead. Must list every user-visible change
from 0.6.2 (US9.3, SC-006):

1. Absent values: `None` → `""`, at every depth
2. Tabs in indentation → `TabIndentationError`
3. Duplicate keys → `DuplicateKeyError`
4. Quoted inline values now decode — and an apostrophe-initial inline value
   (`key: 'Tis`) is now `MalformedQuotedStringError`. More generally, an
   inline value (after `key: ` or `- `) that begins with `'` or `"` must
   be exactly one well-formed quoted string, or it raises: trailing text
   (`title: "Hello" world`) and an invalid escape
   (`path: "C:\Users\me"`, where `\U` wants eight hex digits) both do.
   A double-quoted value whose backslashes happen to form valid escapes
   changes **silently**: `path: "C:\new\temp"` was the literal text with
   its quotes and is now `C:`, a newline, `ew`, a tab, `emp` (pass 26).
   Write such values unquoted or single-quoted
5. `-` / `key:value` fallthrough: bare `-` takes a block value; `key:value` is a
   scalar instead of raising
6. Sibling indentation is now exact (`==`), and a closed key/item accepts nothing
7. Multiline values preserve indentation past the baseline; a below-baseline
   line terminates the value. A root scalar's baseline is column 0, so an
   indented root scalar keeps its indentation: `  hello` was `'hello'` and
   is `'  hello'` (pass 26)
8. Parsimonious exceptions no longer escape; everything is a `ParseError`
9. `ParseError` gains `.message` / `.position` / `.line_text`, and its
   constructor now requires them: `ParseError('msg')` (valid in 0.6.2, where
   it was a bare `ValueError`) is a `TypeError`. `.message` is prefixed with
   the filename when there is one (Contract 05 `error_message`)
10. `Pos` coordinates now refer to the **original** text. `Source` still
    equals a `str` with the same text, but no longer equals a non-`str`
    (`Source('1') == 1` was `True`; red-team pass 20, Contract 08).
    `Source.from_node` takes `(pnode, line, position_map, filename)` instead
    of `(pnode, filename)`; `Pos.from_str_index` and `Source.from_text`
    count only `\n` as a line break (U+2028, U+0085 and the rest no longer
    start a line); and `Source + str` now counts the joining `\n` in
    `end.index` and accepts `''` (red-team pass 23, Contract 08)
11. `load()` accepts binary streams and decodes them as strict UTF-8;
    invalid UTF-8 → `EncodingError`. A text handle decodes with its own
    codec before `load` sees the text: a failure there is also
    `EncodingError`, but a handle in another encoding can decode UTF-8 bytes
    to the wrong characters with no error (cp1252 reads `é` as `Ã©`;
    Contract 06, pass 20), so strict UTF-8 needs `open(p, 'rb')` or
    `encoding='utf-8'`. `filename` now defaults to a `str` or path-like
    `file_obj.name`. `Pos.index` from a default `open(p)` text handle is an
    offset into newline-translated text; editor-grade positions need
    `open(p, 'rb')` or `open(p, encoding='utf-8', newline='')`
12. New: `dumps`, `dump`, and `parse` promoted to a public export (§11.2).
    `syml.parsers.SymlParser` now takes a preprocessed `Document` rather than
    a `filename` and is no longer a whole-document entry point (per-line
    lexing, Contract 02): call `syml.parse` instead
13. Known limitation: deep nesting raises the host `RecursionError` — past
    roughly 500 levels of **block** nesting (one level per line), but past
    only roughly 120 levels of **inline** nesting on a single line
    (`- - - … x`, a ~250-byte input) at CPython's default recursion limit,
    because lexing that one line recurses in Parsimonious. State both figures.
    A deeply inline-nested *string* is not affected in the dump direction:
    `dumps` serializes `'- - … x'` as a quoted value (Contract 07). Deeply
    nested *data* (roughly 1,000 levels of lists or mappings) may raise
    `RecursionError` from `dumps` as well — same deferral. The figures
    scale with `sys.getrecursionlimit()`: about limit/2 block levels and
    limit/8 inline levels, identical on Python 3.12, 3.13, and 3.14 (limit
    300: 148 and 36; limit 10,000: 4,998 and 1,248). With the limit raised
    to 1,000,000, 50,000 levels of inline nesting and of nested lists in
    `dumps` completed without a crash on 3.12 and 3.14 (pass 26). A cyclic
    structure passed to `dumps` raises the same `RecursionError`. Also state
    the memory cost, which nothing bounds while §13.4 is deferred: the
    parse tree takes a few hundred bytes per input byte (about 170 bytes
    per byte retained, measured on a 20,000-line document after pass 26),
    so an application that parses untrusted input should bound its size
    before calling `loads`
14. Typing (red-team pass 20): `loads`/`load` return `SymlData`
    (`str | list[SymlData] | dict[str, SymlData]`) instead of
    `list[Any] | dict[str, Any] | str`, so a typed caller narrows each level
    with `isinstance` before indexing (`r['k']['j']` no longer type-checks
    on the `Any` below the top). `dumps`/`dump` take `SymlInput`
    (`str | list[Any] | dict[str, Any]`), so a `dict[str, str]` passes
    without a cast. Both aliases are exported
15. `dump` writes through the handle's codec: open it with
    `encoding='utf-8'` (§13.3). A locale-default handle can write non-UTF-8
    bytes that `load(open(p, 'rb'))` then rejects (Contract 07)
16. Node-tree and module internals (pass 25). Only `as_data()` and
    `as_source()` on `parse`'s result are the supported tree surface, but
    0.6.2 callers could reach the rest through `syml.parsers.parse`: a
    node's `level` is now its own column (not its line's indent), and
    `set_level` and `IndentNode` are gone; `incorporate_node` and
    `can_add_node` take a second `doc` argument; `source` is a required
    constructor field instead of being derived from `pnode`;
    `KeyLeafNode.key` is removed (use `as_source()`); nodes no longer store
    their Parsimonious `pnode` (pass 26); and `syml.utils`
    (`split_lines`, `get_line`) is deleted (Contract 01)
17. A valueless key inside a list item (`- key:`) takes block content only
    **deeper than the key's own column**, not deeper than the `-` (§9.3
    measured from the key, R-11). A line at the key's column is that key's
    **sibling**. This changes one common layout **silently**:
    `- server:\n  host: x` was `[{'server': {'host': 'x'}}]` and is
    `[{'server': '', 'host': 'x'}]`, with no error. The same layout with a
    list or text under the key (`- key:\n  - x`, `- key:\n  text`) now
    raises `OutOfContextNodeError`. Fix: indent the block past the key
    (`- server:\n    host: x`), which both versions read the same way
    (red-team pass 26; Contract 03's table)
18. §9.0 pre-processing changes values with no error: a CRLF or CR file no
    longer leaves `\r` at the end of every value (`k: v\r\n` was
    `{'k': 'v\r'}`), and one leading U+FEFF is stripped rather than joining
    the first key (`\ufeffkey: v` was `{'\ufeffkey': 'v'}`) (pass 26)

The traceability check is mechanical: every row of the audit's gap list (b)
maps to a numbered entry here or is explicitly out of scope.

**The gap list does not find every change (red-team pass 26).** Notes 4,
7, 17, and 18 were found by running 0.6.2 and the pass 25 assembly over
the same 37 realistic documents and diffing the results. The audit's gaps
are what 0.6.2 got wrong. A side effect of a fix is not a gap, so the
check above cannot find one (note 17 comes from R-11, and note 18 from
§9.0). `CHANGELOG.md` gives each of notes 4, 7, 17, and 18 its old and new
result, in the form written above, so a 0.6.2 user can find their own
layout.

## FR-016 — one conformance ledger

| Artifact | End state | Assertion |
| --- | --- | --- |
| `todo.txt` | retired (deleted) or rewritten as a post-1.0 backlog holding **no** conformance claims | US9.4, SC-007 |
| `CLAUDE.md` § "Spec vs. implementation" | rewritten to state the parser conforms; the "do not assume the parser matches the spec" guidance removed | US9.4 |
| `docs/glossary.md` | seven entries refreshed, four added — see below | |
| `.claude/skills/beads-task-chains/SKILL.md`, `.claude/skills/compound/SKILL.md` | stop naming `todo.txt` as a document or a conformance-findings source once it is deleted (pass 25); US9.4's "exactly one ledger" reads the repository, and the skills are in it | US9.4 |

Recommendation: **delete** `todo.txt`. The audit's section (c) shows it is
superseded or reversed on A1, A3, A4, A9, A10, and section E; what survives
(B3) is FR-017. A rewritten file would carry no live conformance claim, which
makes it a backlog under a misleading name.

### Glossary entries going stale (flagged during planning; three more added in pass 25)

| Entry | Why it goes stale |
| --- | --- |
| `incorporate_node` | described as climbing "by indentation level"; §9.2 climbs by **acceptance**, and level is now the node's own column (R-11) |
| `can_add_node` | described as "the per-node predicate a **container** implements"; `TextLeafNode` and `Mapping` now carry real logic (baseline, duplicate keys) |
| `TextLeafNode` | described as "accepts further `TextLeafNode`s as children" with no conditions; it now carries `inline`, `quoted`, `anchor_level`, and `baseline` and declines more than it accepts |
| `OutOfContextNodeError` | "listed in `unwrapped_exceptions` so Parsimonious does not wrap it" — the tuple now names the base, `(ParseError, RecursionError)`, and line-to-line incorporation raises it outside the visitor altogether (Contract 05), so the entry should say every `ParseError` passes the visitor unwrapped |
| Line node | says every line lexes as `indent (comment / blank / structure / value)`; §4.1 has no `blank` rule and the last alternative is `data`, and blank lines are dropped before lexing (Contract 02; pass 25) |
| Indentation level | "the leading-whitespace depth tagged onto each `SymlNode` when a line node is produced" is exactly the 0.6.2 behaviour R-11 removes: `level` is the node's own column (pass 25) |
| `Pos` | "where a value or key began and ended in the source text" — now the **original** text, before BOM stripping and CRLF/CR normalization (FR-013; pass 25) |

Add: `PositionMap`, `EncodingError`, `dumps`/`dump`, `Document` (original vs
normalized).

## FR-017 — hygiene

| Item | End state | Assertion |
| --- | --- | --- |
| `tests/test_nodes.py` | real tests; the untracked `.orig` folded in or deleted | US9.6 |
| `basetypes.Source.__add__` | dead `return` removed; `str` branch counts the joining `\n` and splits on `\n` only (Contract 08, pass 20) | US9.6 |
| `import syml` | no warning (`python -W error -c "import syml"`) | US9.5, SC-007 |

The `.orig` file is untracked **and** globally gitignored (`*.orig`). The task
must read it, not move it.

## FR-018 — release-ready, not released

No `1.0.0` git tag; no distribution built or uploaded (US9.9). Publishing is a
manual step after merge, and its first action is a commit removing the
`@feature-exit` scenarios (US9.1, US9.9 — see Test obligations) so that CI on
the tagged commit stays green.

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
   `todo.txt` retired, citations point at `SYML-SPEC-REVIEW.md`'s records — the
   D1–D17 decisions **and** the B- and M-numbered findings plan.md's Spec
   Conformance table already cites (B4, M12, M19, …) — and at this feature's
   FR-NNN. Naming only "D1–D17" would leave those citations unrecognized.

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
The three templates (`checklist-`, `plan-`, `spec-template.md`) name neither
`todo.txt` nor principle IV's wording, so none is affected (checked, pass 25).
In the first commit, `CLAUDE.md` changes only to stop restating principle IV's
old wording and to replace the pragma bullet (below); the statement that the parser **conforms** lands with FR-016 at
the end of the feature, when it is true. Rewriting "Spec vs. implementation" in
the first commit would tell every worker in between that an unconformed parser
matches the specification.

**The first commit also retires the pragma guidance this feature contradicts
(pass 25).** Three instructions a worker reads tell it to pragma an
unreachable branch "as in `nodes.py` and `parsers.py`": constitution
principle III's parenthetical, `CLAUDE.md` § Conventions, and the
`pytest-unit-testing` skill's pragma section, whose worked example is
`SymlNode.as_data` with `# pragma: nocover`. Contract 03 gives that exact
method a direct test instead, and Contracts 03/08 add a permanent test that
fails on any `src/` pragma outside `if TYPE_CHECKING:`. Left alone, the
skill steers each worker into a commit the suite rejects, and after the
feature all three point at a pattern that no longer exists. So in the same
first commit: III drops the parenthetical and keeps its permission (a
factual pointer, riding the 2.0.0 bump, no rule changes); the `CLAUDE.md`
bullet and the skill section say that `src/` carries only `if TYPE_CHECKING:`
pragmas, that the test in `tests/test_nodes.py` enforces it, and that an
unreachable stub is deleted or tested directly (Contract 03 § Coverage
without pragmas).

## Leaf ordering for `/sp:05-tasks` (pass 25)

The ordering constraints are stated here once; plan.md and quickstart.md
point here.

1. **First**: the FR-019 amendment commit — constitution 2.0.0 (IV, plus
   III's parenthetical), `CLAUDE.md`'s principle-IV restatement and pragma
   bullet, and the `pytest-unit-testing` skill's pragma section.
2. Behaviour work in the plan's layer order (quickstart.md). Each spec edit
   in the table above lands in the commit whose behaviour it describes; the
   two "post-1.0" markings (§11.3 `DocumentLimitError`, §13.4) describe no
   behaviour, so they land with the §11.3 `EncodingError` edit.
3. `utils.py` and `tests/test_utils.py` are deleted in the commit that
   moves `Pos.from_str_index` to LF-only counting (Contracts 01, 08).
4. **Last**: FR-014's relabel and version bump (with the `dependencies`
   row above), FR-015's `CHANGELOG.md` and
   README section, FR-016's `todo.txt` deletion together with the
   `CLAUDE.md` "parser conforms" rewrite and the two skills' `todo.txt`
   references, and the glossary. US9's `@feature-exit` scenarios go green
   only here.

## FR-020 — Constitution Check

Lives in `plan.md`, not here. See plan.md § "Constitution Check" (US9.8).

## Test obligations

US9's nine scenarios are **repository-inspection** steps, not parser tests. They
bind against file contents, `importlib.metadata.version('syml')`, and
`git tag --list`. Keep them in the acceptance suite (`just acceptance`), where a
non-parser Given/When/Then reads naturally, rather than in the unit run.

### Two scenarios are true only until release (red-team pass 5)

US9.1 (`version == 1.0.0`) and US9.9 (no `1.0.0` tag) describe the state "at
the end of this feature", but `just acceptance` runs in CI on **every** push —
`on: push`, which includes tag pushes, with `fetch-depth: 0`, so tags are
present. Bound as permanent assertions, US9.9 turns CI red on the very commit
that is tagged for release, and US9.1 turns it red on the first 1.0.1 bump.

- Tag both scenarios `@feature-exit` in the `.feature` file. pytest-bdd
  converts a Gherkin `@tag` to a pytest marker of the **same literal string**
  — the hyphen is not normalized — so register `feature-exit: ...` (with the
  hyphen) under `[tool.pytest.ini_options] markers` in pyproject; verified
  against the pinned pytest-bdd 8.1.0 with `--strict-markers`, both for
  collection and for `-m feature-exit` selection. (`just acceptance` itself
  passes `-o addopts=""`, which drops `--strict-markers`, so there an
  unregistered tag is a `PytestUnknownMarkWarning`, not an error; verified,
  pass 25. Registration is still right: it is what the repository's
  convention requires, and it keeps any run that does apply the addopts
  clean.) This is a separate
  mechanism from the project's own `acceptance` marker, which the
  `acceptance-tests` skill applies by hand as `pytestmark =
  pytest.mark.acceptance` at module scope in each binding file — a per-file
  marker cannot distinguish 2 of 9 scenarios in one `.feature` file, which is
  why `@feature-exit` goes on individual Gherkin scenarios instead.
- `@feature-exit` is not a skip marker and `just acceptance` applies no
  deselection for it: both scenarios run, and are expected to pass, on every
  invocation up to and including the commit that removes them. The tag exists
  only to make that removal (FR-018) a `grep`-able, one-step edit; it carries
  no runtime behaviour of its own.
- FR-018's manual release step starts by removing those two scenarios and their
  bindings in a commit **before** creating the tag, so the tagged commit's CI
  run does not carry them (recorded under FR-018 above). This removal is the
  **only** mechanism that keeps CI green across the release — there is no
  conditional skip to fall back on.
- US9.1 reads `pyproject.toml` with `tomllib` as well as
  `importlib.metadata.version('syml')`, so an installed-metadata version that
  lags an edited `pyproject.toml` cannot mask a wrong file.
