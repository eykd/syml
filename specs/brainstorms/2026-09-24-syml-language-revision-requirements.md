---
date: 2026-09-24
topic: syml-language-revision
---

# SYML Language Revision: Values Are Just Text

## Problem Frame

The 1.0.0 conformance build (master `27a3e9a`, tag not yet pushed) was
break-tested on 2026-09-24 against David's stated goal: **make SYML the
easiest YAML-like markup language for real humans to use.** Five lanes
(round-trip fuzzing, grammar probes, API probes, a human-usability lens, and
an independent spec audit) produced 24 confirmed findings, filed under beads
epic `syml-xreq`. Fourteen are defects (code and spec disagree, or the release
text is wrong). Ten were surprises: conforming behavior a human author would
not expect. David ruled on all ten surprises and on the two defects that
needed a design call. Six rulings change the language itself, so the spec
must be revised before the code, and the result is a breaking change against
the current 1.0.0 draft as well as against 0.6.2.

The organizing principle that fell out of the rulings: **values are just
text, all the time.** Structure is decided at the first line of a block and
nowhere else; nothing inside a value is ever reinterpreted.

## Requirements

Every requirement below cites its ruling in `syml-xreq`. The issue carries the
repro, the options considered, and David's comment.

**Language: keys**

- R1. A mapping key matches exactly `[a-z][a-z0-9_-]*` (ASCII, leading
  letter). Any other would-be key line is text. Nothing but indentation spaces
  may precede a key. This subsumes D19's uppercase rule. (`.16`, `.17`)
- R2. `dumps` rejects any key outside R1 as unrepresentable (§11.2.3 follows
  R1). (`.16`)

**Language: values and text context**

- R3. Once a text value is open, every following line at or past its baseline
  is a continuation of that value regardless of its shape (`- x`, `key: v`,
  `key:`, `# x`), until a line below the baseline ends it. Structure is lexed
  only at the first line of a bare `key:` or `-` block and at inline
  positions. A root document whose first line is text is text throughout.
  (`.22`)
- R4. A blank line that sits between two continuation lines of the same value
  is part of the value (a paragraph break). Blank lines before the first
  continuation, after the last, and between items or keys stay inert. (`.15`)
- R5. A root scalar keeps its leading indentation: `  hello` loads as
  `'  hello'` and `  hello\nworld` as `'  hello\nworld'`, as §5.3 already
  says; the root baseline is column 0. (`.2`)
- R6. `dumps` can write everything R3–R5 make loadable: paragraph breaks in
  block form, later lines of any shape, and a root scalar with leading spaces.
  Only a value whose *first* line lexes as structure at a block or list
  position remains unrepresentable. (`.15`, `.22`, `.2`)

**Language: comments**

- R7. SYML has no comments. A line beginning with `#` or `//` is ordinary
  text wherever it appears; §4.3, §5.1 rule 4, and the comment clause of
  §11.2.1 are removed. Consuming applications handle commentary themselves.
  (`.21`)

**Language: whitespace and indentation**

- R8. A tab is accepted as separator whitespace after `key:` and `-`, and
  trailing spaces or tabs after a bare marker are ignored. `dumps` still emits
  one space. (`.19`)
- R9. Only U+0020 is indentation. Every other Unicode White_Space code point
  and every C0/C1 control at the start of a line is content, so an NBSP-led
  line keeps its NBSP, an NBSP-only line is a text line (not a blank), and
  VT/FF/NEL pass through verbatim per §4.6.1. `dumps` refuses a value whose
  line starts with a non-ASCII space only if it would not read back
  identically. (`.1`, `.6`)
- R10. Children are strictly deeper than their parent, lists included: the
  YAML-style indentless sequence (`key:` then `- a` at the key's column) is an
  error. The `- key:` inline-key sibling-column rule of §6.2 stands unchanged:
  `- server:` followed by `host: x` at the key's column is two siblings.
  (`.3`, `.20`)

**Errors**

- R11. `str(ParseError)` reads `<filename>:<line>:<column>: <message>`
  followed by the line text (filename omitted when none). (`.18`)
- R12. An out-of-context error names the column the line sits at and the
  columns that were open, and appends a hint when the failing line or the
  line above would have been a key but for R1, has a tab after its marker, or
  is a list item at its key's column (R10). (`.17`, `.18`)
- R13. Every `ParseError` subclass carries the filename prefix in `.message`
  when a filename is known, and every error position is in original-text
  coordinates (through the BOM and CRLF position map). (`.4`, `.5`)

**API and documentation**

- R14. `dumps` accepts the output of `parse(text).as_source()` by reading
  `Source` keys and scalars as their text. Public docs state that `Source`
  is not a `str`, that an empty `Source` is truthy, and that a multi-line
  `Source.text` is the dedented value. (`.23`)
- R15. The README gains a "Coming from YAML" section listing, in the order a
  YAML user trips over them: no comments, no block-scalar indicators, no
  document markers, no quoting, `null`/`true`/`123` are strings, the R1 key
  rule, the `- key:` sibling-column rule, and paragraph breaks. (`.24`)
- R16. The spec (`SYML-SPECIFICATION.md`), the review doc's D-decisions, and
  the CHANGELOG describe exactly what ships: §4.1's grammar matches the code,
  §8.3's example matches the message, CHANGELOG items 7, 10, 12, 13, 16, 17
  are corrected, and each of R1, R3, R4, R7, R8, R10 is recorded as a new
  D-decision with a breaking-change note. (`.3`, `.8`, `.9`, `.10`)
- R17. `DocumentLimitError` and `EncodingError` are reconciled with §11.3
  (one direction or the other), and the P3 tail is closed: `dumps('')`
  matches its docstring, non-str input to `loads`/`load` raises a clear
  `TypeError`, `load()` honours any `os.PathLike` name, the zero-width
  `Source` of a comment-only document has consistent coordinates. (`.7`,
  `.11`–`.14`)

## Success Criteria

- Every `syml-xreq` child issue is closed with a test that pins its repro.
- The Hypothesis round-trip property (`loads(dumps(x)) == x` for every `x`
  that `dumps` accepts) passes with no excluded family.
- Both fixtures load to their current trees after bar.syml's one same-column
  list is re-indented (R10).
- The lane-4 interactive-fiction documents (prose with colons, capitalized
  `Note:` lines, dash-led lines, paragraph breaks) load as their author
  expected without any error.
- Every spec `**Output:**` example matches the implementation, and the
  grammar printed in §4.1 is the grammar the code runs.

## Scope Boundaries

- No new syntax: no quoting, no escapes, no block-scalar indicators, no
  document markers, no comments. Anything not covered by a ruling stays as
  §1.0 says.
- No configurable limits or `DocumentLimitError` enforcement beyond what R17
  reconciles on paper; recursion and size limits stay documented, not
  enforced.
- `Source` stays a non-`str` class; making it a `str` subclass is a 1.x
  follow-up.
- The three previously filed follow-ups (`syml-xe9b.5`–`.7`) are not part of
  this revision.

## Key Decisions

- Values are just text, all the time (R3): David chose position-based text
  context over per-line structural lexing because it is simpler to reason
  about, at the cost of reintroducing one piece of parser state.
- Strict indentation (R10): David chose spec-as-written over the YAML
  indentless-sequence habit, accepting the fixture edit.
- Comments removed (R7): David chose to delete the feature rather than rule
  on its edge cases; nothing he owns uses comment lines.
- ASCII keys with a leading letter (R1): closes the bracket, quote, and
  leading-digit hazards in one rule; non-ASCII keys are a knowing exclusion.
- Ship as 1.0.0 (R16): the tag is unpushed; no separate 1.0 line to maintain.
- Hints over new API (R12): error improvements stay in the message string;
  no `reason` enum or `expected_columns` attribute.

## Dependencies / Assumptions

- Spec revision lands before implementation; each language change is a
  D-decision in `SYML-SPEC-REVIEW.md` and a CHANGELOG breaking-change item.
- The revision ships as **1.0.0**: the tag is unpushed and every change is
  already breaking against 0.6.2, so there is one breaking release and one
  spec version (David, 2026-09-24).

## Outstanding Questions

### Resolve Before Specify

- None.

### Deferred to Planning

- [Affects R3][Technical] How the tree builder carries "inside an open text
  value" state while keeping per-line lexing.
- [Affects R9][Technical] Adopting the spec's `document = (line "\n")* line?`
  top rule so `indent` can stop consuming `\n`.
- [Affects R4][Technical] Whether pending blank lines are buffered in the
  parser or reconstructed from positions.
- [Affects R6][Technical] The exact residual unrepresentable set once R3, R4,
  R7 shrink §11.2.1.

## Next Steps

-> `/sp:02-specify syml language revision: values are just text` to create
the formal specification from this document.
