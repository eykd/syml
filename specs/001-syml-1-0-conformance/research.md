# Phase 0 Research: syml 1.0 Spec Conformance

**Feature**: `001-syml-1-0-conformance` | **Date**: 2026-09-21
**Input**: `spec.md` (FR-001..FR-020), `specs/brainstorms/2026-09-14-*`,
`SYML-SPECIFICATION.md`, `SYML-SPEC-REVIEW.md` (D1–D17), `todo.txt`

This document resolves every NEEDS CLARIFICATION carried into planning. The
spec's Assumptions section lists six "Deferred to Planning" items; two further
questions (acceptance-suite source, `EncodingError`'s parent) were raised in the
same section. All eight are settled below as R-01..R-08. R-09..R-11 record
design choices that the contracts depend on but that the spec left to planning
by omission.

---

## R-00: Audit re-confirmation (spec Assumptions, last bullet)

**Decision**: The audit's 21 gaps still hold at `HEAD` (`4f7ba43`). Re-verified
2026-09-21 by replaying seventeen of the audit's repro inputs through the
installed parser. Every one reproduced the audit's recorded "got" value exactly,
including the two `SyntaxWarning: invalid escape sequence '\s'` emissions at
import, `hasattr(syml, 'dumps') is False`, and `pyproject.toml` still declaring
`version = "0.6.2"`.

**Rationale**: The spec makes re-confirmation a first planning step. Nothing
between commit `2bfd6e6` (audit) and `4f7ba43` (HEAD) touched `src/syml`.

**Alternatives considered**: Re-running the full 53-block extraction harness.
Rejected — the harness was deliberately not committed (`tools/` is under the
coverage and mypy gates), and the seventeen probes cover every root-cause row in
audit table (a) plus the three hygiene items.

---

## R-01: D15's `White_Space` set vs Python `re`'s `\s` vs §4.1's key class

_(spec Assumptions, item 1; affects R4/FR-004; `todo.txt` A5; D15)_

**Question**: Which rule rejects `key\x1cname: v`, and does it reject it as
scalar fallthrough or as an error?

**Empirical finding** (2026-09-21): the symmetric difference between Python
`re`'s Unicode `\s` on `str` and D15's enumerated `White_Space` set is exactly
`{U+001C, U+001D, U+001E, U+001F}` — those four are in Python's `\s` and not in
D15. D15 contains nothing Python's `\s` misses. All four sit inside
`\x00-\x1f`, which §4.1's key class already excludes independently.

**Decision**:

1. `key\x1cname: v` is **not** a key-value pair, and is **scalar fallthrough**
   (§7.6), not an error. Both candidate rules agree on this outcome, so the
   question has no observable consequence: the `\x00-\x1f` clause decides it.
2. The grammar transcription MUST NOT write `\s` in the key class. It
   enumerates D15's set explicitly:
   `key = ~"[^\x00-\x20\x7f-\xa0\x85\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000:]+"`
   (the `\x00-\x20` run subsumes `\t\n\v\f\r` and the space; `\x7f-\xa0`
   subsumes U+0085 and U+00A0).
3. `SYML-SPECIFICATION.md` §4.5 gains one clarifying sentence recording finding
   (1): the `\x00-\x1f` exclusion and the `White_Space` exclusion overlap, and
   the C0 exclusion is what decides U+001C–U+001F. No normative change.

**Rationale**: D15 says implementations "MUST use this exact set, not a host
regex engine's default `\s`". Enumerating satisfies that literally and
side-steps a second, unrelated defect: Parsimonious evaluates a `~"..."` atom's
body as a Python string literal, so a bare `\s` inside the grammar is what emits
the two `SyntaxWarning`s at import (audit gap #20, FR-017). Enumerating fixes
hygiene and conformance in one edit.

**Alternatives considered**:

- **Keep `~"[^\s:\x00-\x1f\x7f-\x9f]+"` and rely on Python's `\s` being
  Unicode-aware.** Rejected: behaviourally identical today, but it makes the
  implementation's conformance contingent on a host-regex detail D15 explicitly
  forbids relying on, and it keeps the `SyntaxWarning`.
- **Escape it as `\\s` to silence the warning only.** Rejected: fixes the
  warning without fixing the D15 violation.
- **Switch to the `regex` module for `\p{White_Space}`.** Rejected: `regex` is
  already a declared dependency but is unused by `src/`; Parsimonious compiles
  its own atoms with `re`, so this would mean replacing the grammar engine.
  Constitution principle V (no gratuitous dependency growth) points the other
  way — and the enumerated class is a strictly local change.

---

## R-02: Mapping normalized-text positions back to original-text positions

_(spec Assumptions, item 2; affects R13/FR-013)_

**Decision**: An **offset table** built during §9.0 pre-processing, threaded
into `Source.from_node` as a `PositionMap`. Specifically:

- `line` is **identical** in both texts. §9.0 replaces each `\r\n` and each bare
  `\r` with exactly one `\n`, one break for one break; no step adds or removes a
  line boundary. No remapping needed.
- `column` is identical, with one exception: on line 1 only, a stripped BOM
  shifts every column by +1.
- `index` is the only field needing real work:
  `original = normalized + bom_offset + (count of CRLF pairs at or before this
  normalized index)`. A bare `\r` → `\n` is a one-for-one substitution and
  contributes nothing; only `\r\n` → `\n` loses a character.
- Implementation: `PositionMap` holds `bom_offset: int` (0 or 1) and a sorted
  `list[int]` of the normalized indices at which a CRLF was collapsed. `to_original`
  uses `bisect_right` — O(log n) per lookup, O(n) to build, no per-character table.

**Rationale**: §4.1 opens by stating the grammar "assumes §9.0's pre-processing
has already been applied to the input; no rule below needs to handle a bare `\r`
or a leading BOM." Parsing the original text with a CR-tolerant grammar
contradicts that premise directly, and would need every downstream rule to
tolerate `\r`. The offset table keeps the whole concern at the pre-processing
boundary, which is where the spec puts it.

Note this decision is entangled with audit gap #16: `utils.split_lines` uses
`str.splitlines()`, which recognizes U+2028/U+0085/U+000B/U+000C as breaks and
so miscounts lines in the *normalized* text before any remapping is attempted.
§13.3 forbids that explicitly ("Implementations MUST NOT use a general-purpose
'split into lines' library routine"). The fix (split on `\n` only) is a
prerequisite for R-02 and is contracted separately.

**Alternatives considered**:

- **Parse the original with a CR-tolerant grammar.** Rejected as above; also
  fails the BOM case (a leading BOM would become part of the first key, which is
  audit gap #8's exact symptom).
- **A full per-character index array.** Rejected: O(n) memory on a 10 MiB
  document for information a two-field struct carries.
- **Report normalized coordinates and expose a `to_original()` helper on
  `Pos`.** Rejected under principle VI — see plan.md's Constitution Check entry
  for FR-013; it doubles the public surface and leaves the default wrong for the
  editor-integration use case that is source tracking's whole point.

---

## R-03: `ParseError.position` shape, and which errors carry `line_text`

_(spec Assumptions, item 3; affects R9/FR-009; §11.3; `todo.txt` B2)_

**Decision**: `.position` is always a `Pos` (never a bare line number, never
`None`), and `.line_text` is always a `str` (the empty string when the offending
position is past the last line). **Every** `ParseError` subclass carries both.

```python
class ParseError(ValueError):
    def __init__(self, message: str, position: Pos, line_text: str) -> None: ...
    message: str
    position: Pos
    line_text: str
```

Per-class position anchor and extra attributes:

| Class | `position` anchors at | Extra attributes |
| --- | --- | --- |
| `OutOfContextNodeError` | start of the offending node | — |
| `DuplicateKeyError` | start of the repeated key | `key: str`, `first_position: Pos` |
| `TabIndentationError` | the **first tab** in the line's leading whitespace | — |
| `MalformedQuotedStringError` | the **opening quote** character | `escape: str \| None`, `code_point: int \| None` |
| `EncodingError` | see R-04 | — |

All positions are original-text coordinates (R-02).

**Rationale**: §11.3 states flatly that "Every subclass below carries: message,
position: Pos, line_text" — the shape is not actually open; what was open is
whether every class can produce one. Each can: `TabIndentationError` and
`EncodingError` are raised inside pre-processing, where the raw text and the
current offset are both in hand; the others are raised with a node or token in
hand. Making the attributes non-optional means a caller never has to branch.

The current implementation passes them as positional `ValueError` args
(`raise OutOfContextNodeError('...', pos, line)`), so `.args` carries them but
no named attribute exists. Keeping `super().__init__(message, position,
line_text)` preserves the existing `.args` tuple while adding the named
attributes, so no currently-working `except ParseError as e: e.args[1]` breaks.

**Alternatives considered**:

- **`position: Pos | None`, populated only where cheap.** Rejected: §11.3's
  wording is unconditional, and optionality pushes a `None` check into every
  caller — the same defect FR-005 is closing on the data side.
- **`.position` as a line number `int`.** Rejected: loses column and index, and
  §11.3 names the type `Pos`.
- **`line_text` only on line-scoped errors.** Rejected: `EncodingError` is the
  only awkward case and R-04 gives it a well-defined line.

---

## R-04: `EncodingError`'s parent, and its position

_(spec Assumptions, penultimate bullet; FR-009, FR-010; §11.1, §11.3)_

**Decision**: `EncodingError(ParseError)`. §11.3 gains the entry. It is the
plain reading of §11.1's "MUST raise a `ParseError` (or a clearly-documented
decoding exception callers can distinguish from a successful parse)", and the
spec already adopts it; planning confirms rather than revisits it.

Because R-03 makes `position` and `line_text` non-optional, `EncodingError`
needs both from a `UnicodeDecodeError`, whose `.start` is a **byte** offset —
not a code-point index. Resolution:

1. Decode the valid prefix: `raw[: err.start].decode('utf-8')` (guaranteed to
   succeed; UTF-8 is self-synchronizing and `err.start` is a sequence boundary).
2. `position.index` = length of that decoded prefix in code points.
3. `position.line` = 1 + number of line breaks in the prefix, counting `\r\n`,
   bare `\r`, and `\n` each as one (the raw text has not been normalized yet,
   because it cannot be decoded).
4. `position.column` = code points since the last break.
5. `line_text` = the decoded prefix's final partial line. It is necessarily
   truncated at the bad byte; the contract says so.

These are original-text coordinates by construction — the offending bytes never
reach normalization, so R-02's `PositionMap` is not involved.

**Rationale**: byte-vs-code-point is the only real trap here, and it is
invisible until a non-ASCII character precedes the bad byte. Pinning it in the
contract stops a plausible off-by-N.

**Alternatives considered**:

- **`EncodingError(ParseError, UnicodeDecodeError)`.** Rejected:
  `UnicodeDecodeError` is a `ValueError` subclass with a five-argument
  constructor whose `.args` shape conflicts with R-03's, and multiple
  inheritance buys a caller nothing §11.3 asked for.
- **Re-raise `UnicodeDecodeError` unchanged, documented.** Rejected: FR-009 says
  no non-`ParseError` escapes `loads`/`load`, and SC-005 measures it.
- **Give `EncodingError` `position = Pos(0, 1, 0)` and `line_text = ''`.**
  Rejected: cheap, but an editor integration pointing at byte 0 of a 4 MiB file
  is worse than no position at all.

---

## R-05: Fixture strategy for examples with trailing whitespace

_(spec Assumptions, item 4; affects R1/FR-001; spec Edge Cases)_

**Problem**: `.pre-commit-config.yaml` runs `trailing-whitespace` and
`end-of-file-fixer` over every file in the repo. The spec's `key:` + trailing
space, `- ` (marker plus space), and the §7.5 preservation cases cannot survive
as literal file content, in a `.feature` file or a Python triple-quoted literal
alike. §7.5's own Editor Compatibility Note says the same thing about editors.

**Decision**: **Every** SYML fixture in the test suites — acceptance and unit —
is written as a **single-line double-quoted Python/Gherkin string using escape
sequences**, never as a multi-line literal.

- Gherkin: `Given a SYML document "key:\n  first\n    indented\n  back"`. One
  shared step definition in `tests/acceptance/conftest.py` applies
  `codecs.decode(raw, 'unicode_escape')`... **no** — it uses an explicit,
  audited unescape table (`\n \t \r \\ \" \uXXXX \UXXXXXXXX`), because
  `unicode_escape` decodes via latin-1 and mangles non-ASCII content, which
  US2/US3/US8 fixtures contain (U+FEFF, U+2028, U+00A0).
- Python unit tests: ordinary `'key:\n  a\n b'` literals. Never `"""..."""`.
- The `\x20` escape is the canonical way to write a significant trailing space:
  `"key:\x20"`, `"-\x20"`. It reads as deliberate rather than as an accident an
  editor will silently repair.

**Rationale**: a single rule that covers every case, verifiable by grep
(`rg '"""' tests/` must find no SYML document literals), beats a per-case
workaround. It also makes every fixture diff-legible: a trailing space is
visible as `\x20` in review, where a literal one is not.

**Alternatives considered**:

- **Exclude `specs/acceptance-specs/` from the `trailing-whitespace` hook.**
  Rejected: the hook is a guardrail the project deliberately runs, editors strip
  the same whitespace anyway (§7.5's note), and it would make fixture
  correctness depend on every contributor's editor config.
- **Base64 or hex-encoded fixture files.** Rejected: unreviewable.
- **Construct the affected documents in a Python helper and pass a fixture
  name through Gherkin.** Rejected: indirection for a subset of cases, and the
  escape-string rule covers them uniformly.

**Note, in scope for this plan's own artifacts**: the same hook runs on
`plan.md`, `research.md`, and `contracts/*.md`. Any `key:` + trailing space
inside a fenced block in these documents would be silently stripped at commit.
Every such example in this feature's planning artifacts is therefore written
with a visible `␠` marker (U+2420 SYMBOL FOR SPACE) and a note, never with a
literal trailing space.

---

## R-06: `dumps` output format for nested structures

_(spec Assumptions, item 5; affects R11/FR-011; §11.2.1)_

**Decision**: §11.2.1 rules A–G fix the quoting and the one-space-after-`-`
rule. Everything else is an **implementation choice**, documented in the
docstring and in the README's serializer section:

| Choice | Value | Why |
| --- | --- | --- |
| Indent width | 2 spaces per level | Every example in the specification uses 2. |
| Blank lines between entries | none | §12.1's example has them; nothing requires them; omitting keeps output canonical. |
| Trailing newline | exactly one | §4.8 makes it equivalent; `end-of-file-fixer` expects it. |
| Key order | insertion order | D8 — normative, not a choice. |
| Mapping-valued key | `key:` + indented block | the only form §7.2 leaves available. |
| List-valued key | `key:` + indented `-` lines | same. |
| List item holding a mapping | `- k: v`, siblings at the key's column | §11.2.1 rule G + §6.2/M23. |
| List item holding a list | `-` + indented `-` lines | §7.2's `- - x` nests. |

Two further calls the spec does not make:

- **Non-string leaves** (`dumps(5)`, `dumps(None)`, `dumps(True)`) raise
  `TypeError`, not `UnrepresentableValueError`. §11.2.2–.4 enumerate
  *representable-type* values with no SYML *encoding*; an `int` is not a SYML
  value at all. `UnrepresentableValueError` is a `ValueError` and would read as
  "this string cannot be written", which is a different failure.
- **`dump(value, fp)`** accepts a text stream only (`IO[str]`). `load` accepts
  both text and binary because callers already hold `open(p, 'rb')` handles;
  there is no equivalent installed-base argument for the write direction, and
  `TextIOWrapper` is one line away. Asymmetry is recorded in the contract.

**Rationale**: SC-003 measures `loads(dumps(x)) == x`, which the quoting table
alone guarantees; format choices below that are cosmetic and must not be
asserted as spec conformance, or the test suite will encode a fiction.

**Alternatives considered**:

- **Emit 4-space indents.** Rejected: every specification example is 2.
- **Insert a blank line between top-level keys** (as §12.1 does). Rejected:
  makes `dumps(loads(dumps(x)))` differ from `dumps(x)` in whitespace for no
  gain; a canonical serializer should be idempotent as text.
- **`UnrepresentableValueError` for non-string leaves.** Rejected as above.

---

## R-07: Whether `Source`'s text-equality needs to change

_(spec Assumptions, item 6; affects R12/FR-012; §10.3; audit m4)_

**Decision**: **No change.** `Source.__eq__` and `__hash__` stay text-based.
The `# pragma: no cover` on `__hash__` is removed and it is tested directly
(FR-012); the dead `return self + other.text` after the `isinstance(other,
Source)` branch's `return` is deleted (FR-017, `todo.txt` B3).

**Rationale**: §10.3 does not merely tolerate text-equality, it *requires* it —
"Source objects SHOULD be usable as dictionary keys interchangeably with
strings" — and then draws the exact consequence this question was asking about:
"Because Source objects compare and hash exactly as their text, an
implementation MUST NOT rely on final mapping construction to detect duplicate
keys... Duplicate-key detection MUST occur during tree incorporation, before the
mapping is materialized." FR-007 lands that detection. The collision hazard is
therefore closed from the other end, by design, and weakening `Source`'s
equality would break the interchangeability §10.3 asks for.

**Alternatives considered**:

- **Identity- or position-based `__hash__`.** Rejected: directly contradicts
  §10.3 and breaks `loads(...)["key"]`-style access on a source-mode tree.
- **A `__eq__` that compares position when both sides are `Source`.** Rejected:
  makes equality non-transitive against `str` and would silently change
  `as_source()` mapping construction.

---

## R-08: Acceptance-suite source — extract from the spec, or hand-transcribe?

_(spec Assumptions, penultimate-but-one bullet; SC-001)_

**Decision**: **Both**, with distinct jobs.

1. **Gherkin per user story**, in `specs/acceptance-specs/US<NN>-<slug>.feature`,
   bound in `tests/acceptance/test_us<nn>_<slug>.py`, hand-transcribed from the
   spec's Acceptance Scenarios. This is the ATDD outer loop the `/sp:*` workflow
   and `ralph` depend on; it runs under `just acceptance`.
2. **A spec-extraction test**, `tests/test_spec_examples.py`, which at collection
   time walks `SYML-SPECIFICATION.md`, pulls every fenced ` ```syml ` block
   followed by an `**Output:**` line, and parametrizes one case per block
   (JSON output → assert `loads(...) == parsed`; `ERROR: X` → assert
   `pytest.raises(X)`). It runs in the ordinary unit suite.

**Rationale**: SC-001 says "53 today, **and the count tracks the specification as
it is edited**." Only extraction can satisfy that clause — a hand-transcribed
suite silently stops covering a block the moment someone edits the spec, which
FR-019's amendment explicitly makes likely during implementation. Conversely,
extraction alone cannot satisfy the ATDD loop, because the spec's blocks are not
organized by user story and several acceptance scenarios (US5's import assertions,
US7's round-trip property, all of US9) have no fenced block at all.

**Placement**: the extractor lives under `tests/`, not `tools/` and not `src/`.
`tools/` is inside the coverage gate and the extractor's error paths are hard to
exercise; `tests/` is inside the mypy file set but outside the coverage gate,
which is the right combination. `pyproject`'s coverage config covers `src/` and
`tools/` only, so no pragma is needed.

**Guard**: the extractor asserts a minimum block count (currently 53) so a
regex-drift bug that silently finds zero blocks fails loudly rather than passing
vacuously.

**Alternatives considered**:

- **Extraction only.** Rejected: no ATDD loop; `sp:05-tasks` and `ralph` both
  require per-story `.feature` files.
- **Gherkin only.** Rejected: fails SC-001's tracking clause.
- **Commit the audit's extracted `examples.json` as a static fixture.**
  Rejected: same drift problem as hand-transcription, with less readability.

---

## R-09: The third-party-exception boundary (FR-009)

_(not in the deferred list; a design choice FR-009 forces)_

**Problem**: `syml.loads('key:value')` raises
`parsimonious.exceptions.IncompleteParseError` today (audit gap #12,
`todo.txt` B2). Two structurally different causes produce it: a line no
structural rule matches (`key:value` — must become a scalar), and the PEG
stranding case (`key: "a" trailing` — `key_value`'s quoted alternative matches
the prefix, then the line cannot complete; must become
`MalformedQuotedStringError`).

**Decision**: **Split the document on `\n` first and lex each physical line with
`grammar['line'].parse(...)`.** The `document` rule stays in the grammar text
for fidelity with §4.1 (and for D16's non-nullable-repetition property) but is
not the entry point.

Consequences:

- §9.1's steps read literally: 1 pre-process, 2 split into lines, 3 lex each
  line independently, 4 build tree, 5 convert. §5.1 rule 6's
  "each line is lexed independently of its position in the document" becomes
  structural rather than incidental.
- A per-line `IncompleteParseError` means exactly one thing: *this line did not
  fully lex*. With `data = ~"[^\n]*"` as the final alternative, the only way a
  line fails to fully lex is a `quoted_value` that closed and was followed by
  non-whitespace — precisely §4.7's trailing-content case. So the boundary
  handler classifies it as `MalformedQuotedStringError` and there is no residual
  "unknown parse failure" bucket.
- Line/column bookkeeping becomes trivial: each line knows its own start offset
  in the normalized text, so `pnode.start` + `line_start` gives the document
  index without re-deriving it.
- Every call into Parsimonious is wrapped; `ParseError` and its subclasses stay
  in `unwrapped_exceptions` so the tree builder's own raises pass through.

**Alternatives considered**:

- **Parse the whole document with `document` and translate boundary errors.**
  Rejected: to classify a stranding it must re-derive which line stranded and
  re-lex it anyway, so it pays the per-line cost *plus* a whole-document parse,
  and the failure mode ("something on or before offset N") is strictly less
  informative.
- **Catch `parsimonious.exceptions.ParseError` and re-raise a generic
  `syml.ParseError`.** Rejected: satisfies FR-009's letter but turns
  `key: "a" trailing` — a case the spec names explicitly in §7.6's table — into
  the wrong exception class, failing US6 scenario 6.

---

## R-10: Where the quote-guard rule lives (FR-008)

**Decision**: §4.1's quote-guard is a **visitor post-check**, not a grammar
rule. §4.1 says so itself: "normative, not expressible in PEG alone". After
`key_value`'s second alternative (`key_colon ws data`) or `list_item`'s inline
`value` produces a `data` match, the visitor inspects its first character; `'`
or `"` raises `MalformedQuotedStringError`. The check is line-local and consults
nothing outside the current line, so the grammar stays context-free at the
lexing level (constitution principle V).

**Alternatives considered**: a negative lookahead in the grammar
(`data = !~"['\"]" text` at the inline positions). Rejected: it makes the line
fall through to a *different* alternative rather than raising, which reintroduces
exactly the silent fallthrough D2 rejected.

---

## R-11: `level` is the node's own column, not the line's indentation (FR-006)

**Decision**: a node's `level` is the 0-indexed column at which **its own**
structural marker or content begins, per §9's definition ("the column index
where the node's structural marker (`-` for list items, key name for mappings)
or content begins"). It is computed as `pnode.start - line_start`, not inherited
from the line's `indent` token.

The current `visit_line` does `value.set_level(indent.level)` and `set_level`
recurses into `children`, so an inline structure built on a list-item line
inherits the *line's* indent. That is the direct cause of audit gap #14 / M23:
`-   name: Alice` registers the mapping at column 0 instead of column 4, so
`role: admin` at column 2 is wrongly accepted. US1 scenario 8 measures it.

**Alternatives considered**: keeping `set_level` recursive and special-casing
the list-item inline slot. Rejected: the general rule is simpler than the
special case, and §9's definition is already the general rule.

---

## Carried forward from the brainstorm — do not re-explore

These were settled in `specs/brainstorms/2026-09-14-syml-1.0-spec-conformance-requirements.md`
("Key Decisions") and are recorded here so Phase 1 and the red-team pass do not
re-open them.

| Settled | Rejected alternative |
| --- | --- |
| The spec text labelled v1.1 **is** the 1.0 spec; relabel at release, folding §14's two entries into one. | Ship as "1.1" and leave the history split. |
| `dumps`/`dump` are **in scope** for 1.0. | Defer the serializer to 1.1 — "a 1.0 that cannot round-trip is a half-conforming 1.0". |
| **D17 stands**: no root-scalar quoting; `dumps` raises. | Add a third quoting context and a new grammar rule at the root position. |
| **Clean break** from 0.6.2, documented in migration notes. | A 0.7 bridge release or compatibility flags — code written only to be deleted at 1.0. |
| **All §13.4 limits deferred** past 1.0 (depth, line length, document size, `DocumentLimitError`); deep nesting keeps raising the host `RecursionError`, documented as a known limitation. | Ship limits in 1.0; ship `DocumentLimitError` as an eighth exported class. |
| **Spec is open during implementation** — the implementer may edit spec text when implementation exposes a defect, provided the edit lands in the same commit as the behaviour it changes. | Require a separate decision gate before every spec edit (constitution IV as written). Amended under FR-019. |
| **One feature, one epic**, despite the size. | Split into per-area features. |
| **Source positions in original text** (FR-013). | Normalized coordinates, or a dual surface. |
| **`load()` accepts text and binary streams** (FR-010). | A separate `loadb()`. |
| **`todo.txt` is superseded**, not merged: its A1 open question is decided (`MalformedQuotedStringError`), A3/A4 are reversed on class, A9 is superseded by D11, A10 by D16, and three "already conformant" section-E claims are now false. | Keep `todo.txt` as a live second ledger. |

---

## Open items handed to `/sp:04-red-team`

None blocking. Two worth an adversarial look:

1. **R-09's claim that a per-line `IncompleteParseError` can only mean
   trailing-content-after-quote.** It rests on `data = ~"[^\n]*"` being the last
   alternative of every path. A red-team pass should try to construct a
   counterexample line that lexes partially and strands for a different reason.
2. **R-02's claim that `line` needs no remapping.** It rests on §9.0 being
   exactly one-break-for-one-break. A red-team pass should check the boundary
   cases: a document ending in a bare `\r`, and `\r\r\n`.
