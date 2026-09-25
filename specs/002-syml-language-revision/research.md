# Research: SYML Language Revision — Values Are Just Text

**Feature**: `002-syml-language-revision` | **Date**: 2026-09-24 | **Plan**: [plan.md](./plan.md)

Every open item the spec carried into planning is settled here. R-01 to R-04
are the four "Deferred to Planning" items from the brainstorm (spec
Assumptions (a)–(d)). R-05 to R-12 are spec questions that surfaced while
planning, including three places where the spec contradicted itself. R-13 to
R-17 record tooling and process decisions. R-18 records the principal's
comment ruling of 2026-09-24 and the mechanism chosen for it.

Evidence for the design decisions comes from a throwaway spike: a copy of
`src/syml` in the session scratchpad with the R-01/R-02/R-03 changes applied
and the serializer cut to the R-05 residual set. The spike ran every
parse-side acceptance scenario of User Stories 1 and 2 (70 inputs), both
repository fixtures, all 34 lane-4 documents, and a Hypothesis round trip
(5,000 examples) plus a minimality probe over refused values. Results are
quoted where they settle a question. The spike is not a deliverable; the
contracts are.

Alternatives the brainstorm already rejected are not re-explored here: option
(a) and (c) of each `syml-xreq` ruling (keep as-is, or the heavier variant)
are recorded in the issues and in the brainstorm's Key Decisions; D20–D25
cite them as their "alternative not taken".

---

## R-01 — Carrying "inside an open text value" state (Deferred item a; FR-003)

**Decision**: No new parser or builder state. The tree builder's tip already
*is* the state. When the tip is a `TextLeafNode`, the value is open; when a
line at or past that value's threshold is offered to it, the line is text
regardless of how it lexed.

Mechanism, in `TextLeafNode.incorporate_node` (Contract 02):

1. Factor `TextLeafNode.can_add_node`'s level rule into
   `accepts_level(level) -> bool` (baseline unset: `level > anchor_level`;
   baseline set: `level >= baseline`).
2. If the offered node is not a `TextLeafNode` and `accepts_level(node.level)`
   holds, replace it with a `TextLeafNode` built over the line's **content
   span** (everything after the indentation), then incorporate that.
3. Otherwise delegate unchanged: a below-threshold line walks up exactly as
   in 1.0 (§5.3's re-offer; US1 scenarios 13 and 18 still hold).

The content span is recorded by the line visitor: `visit_line` sets
`node.content_pnode` to the parse node of the `(structure / data)` choice.
This is needed because a `KeyValue`'s own `pnode` covers only `key:`, not the
inline value after it, so the structural node alone cannot be re-read as the
whole line.

Root falls out with no special case beyond R-12: a root scalar's baseline is
0, every line is at level ≥ 0, so a document whose first line is text is text
throughout.

Lexing stays per-line and context-free: every line still lexes as
`structure` or `data` on its own characters. Only the tree builder decides
that an already-open text value swallows it. Constitution principle V's
"context-free at the lexing level" is therefore kept, and the plan's
Constitution Check says so.

**Spike evidence**: all 18 US1 scenarios pass, including 3, 4, 14, 15, 16,
17, 18; SC-004's four lane-4 documents load to the ruled values.

**Alternatives considered**:

- *A mode flag in the builder loop* (`in_text = True` until a dedent). Rejected:
  it duplicates the baseline arithmetic `TextLeafNode` already owns, and the
  flag must be reset on every walk-up path.
- *Context-sensitive grammar* (a second `continuation_line` rule chosen by the
  parser). Rejected: Parsimonious has no way to choose a rule by indentation,
  and it would break principle V.
- *Re-lexing a line as `data` when the tip is text* (a second parse per line).
  Rejected: the content span is already in the parse tree; re-parsing is
  wasted work and a second source of truth for the line's text.

---

## R-02 — Adopting `document = (line "\n")* line?` with spaces-only `indent` (Deferred item b; FR-009, FR-016)

**Decision**: Adopt the spec's top rule and make the code's grammar the one
§4.1 prints. The grammar changes land as **one atomic leaf** (top rule,
`indent`, `ws`, `key`, `eol`, and the `comment` change: removal as first
planned, narrowed to column 0 by R-18), because intermediate states
stall the parse (lane 2 verified that swapping `indent` alone stops after
line 1).

The revised rule set (full text in Contract 01):

```peg
document        = (line "\n")* line?
line            = comment / (indent (structure / data))
comment         = ~"(?:#|//)[^\n]*"
structure       = list_item / key_value / section
indent          = ~" *"
list_item       = value_list_item / guard_list_item
value_list_item = "-" ws value
guard_list_item = "-" &eol
key_value       = key_colon ws data
section         = key_colon &eol
key_colon       = key ":"
key             = ~"[a-z][a-z0-9_-]*"
eol             = &"\n" / ~r"\Z"
ws              = ~"[ \t]+"
text            = ~"[^\n]*"
value           = structure / data
data            = text
```

Consequences the implementation must handle (all confirmed in the spike):

- **`line` is nullable.** A document ending in `\n` yields a trailing
  zero-length line, and every blank line yields a zero-length `data`. The old
  `blank = &eol` rule absorbed this implicitly. `visit_line` returns `None`
  when the content span is empty **or consists only of spaces and tabs**
  (the §4.4/§9.0 step 3 definition of blank; with `indent` now spaces-only, a
  line such as `  \t` lexes as `indent` + `data "\t"` and must still be
  blank). No `blank` rule is added: §4.4 states the classification.
- **`generic_visit` collapses single-child groups** to a bare node, so
  `visit_document` flattens `Node | list | None` explicitly before walking.
- **`eol` is lookahead-only.** Nothing but `document` consumes `\n`.
- **Rule names follow the spec** where the spec's are clearer: code's
  `section` (key + colon) becomes `key_colon`, code's `section_line` becomes
  `section`. The spec adopts the code's two *named* `list_item` alternatives
  (`value_list_item`, `guard_list_item`), because the visitor needs a hook
  for each and an anonymous parenthesized alternative has none.
- **Deleted with the grammar**: `visit_blank`, `visit_indent`, `IndentNode`,
  `Comment`, `SymlNode.comments` (`visit_comment` stays and returns `None`,
  R-18),
  `key_has_uppercase`, `_is_text_line`, `_text_leaf`, `_UPPERCASE_CATEGORIES`,
  and the `unicodedata` import (FR-001 makes D19's out-of-PEG check
  unnecessary: the key class is ASCII lowercase by construction).
- **The whole-document parse stays.** `parse()` runs one grammar parse over
  the normalized text, as today. (001's plan described per-line parsing as the
  entry point; the shipped code never did that, and nothing here needs it.)

"The same rule set" (US4 scenario 2, SC-005) is checked by a test that loads
the fenced `peg` block of §4.1 with `parsimonious.Grammar` and compares each
rule's `as_rule()` text against `SymlParser.grammar`, name by name. That
ignores comments and alignment, which the spec keeps for readers.

**Alternatives considered**:

- *`indent = ~"[ \t]*"`* (lane 2's verified fix shape). Rejected: FR-009 and
  US4 scenario 2 fix `indent` as spaces-only; the tab scan (§9.0) already
  raises before the grammar sees a tab in indentation, and tab-only lines are
  handled by the blank classification above.
- *Keep `lines = line*` and reprint §4.1 from the code.* Rejected: the old top
  rule depends on `indent = \s*` swallowing the previous line's `\n`, which is
  the root cause of `syml-xreq.1`.
- *A `blank` alternative inside `line`.* Rejected as redundant: a
  whitespace-only content span is already recognizable in the visitor, and
  the spec's grammar text stays one rule shorter.

---

## R-03 — Paragraph breaks: buffered or reconstructed? (Deferred item c; FR-004)

**Decision**: Reconstruct from positions at attach time; never buffer.

Blank lines never reach the tree builder (R-02: `visit_line` drops them).
When `TextLeafNode.add_node` appends a continuation, it counts the blank
lines in the normalized text between the previous line of the value and the
new one:

```text
previous = self.children[-1] if self.children else self
gap = full_text[previous.pnode.end : node.pnode.start]
node.blank_lines_before = sum(1 for line in gap.split("\n")[1:-1] if is_blank(line))
```

`as_data` emits `blank_lines_before` empty lines before each continuation.
(R-18 replaced this pass's `gap.count("\n") - 1`, which counted a column-0
comment line as a blank line.) The normalized text is LF-only, so the count
is exact whatever the original line endings or BOM. Between two lines of the
same value every intermediate line must be blank or a column-0 comment: any
other line at or past the threshold would have been absorbed as a continuation (R-01), and one below it would have ended the
value, after which the tip never returns to it.

Inertness at the edges comes for free: a blank line before a block value's
first line, after a value's last line, or between items and keys is never
between two lines of one value, so nothing records it. A value therefore
never begins or ends with an empty line (FR-004). A whitespace-only line
contributes one empty line, not its spaces (spec Edge Cases).

**Spike evidence**: US1 scenarios 1, 2, 11, 12, 13 pass; `k:\n  a\n      \n  b`
gives `{"k": "a\n\nb"}`.

**Alternatives considered**:

- *Buffer pending blank lines in the builder loop* and flush them into the
  next continuation. Rejected: needs a buffer that every non-continuation path
  must discard, and a buffered blank node risks leaking into `Root` as a text
  scalar for a blank-led document.
- *Diff `source.start.line` numbers at `as_data` time.* Equivalent result, but
  it reads positions after original-text re-anchoring; the normalized-text
  count is local to parsing and does not depend on `PositionMap`.

---

## R-04 — The inline-value blank line: is `k: first\n\n  second` a paragraph break? (FR-004 ambiguity)

**Question**: FR-004 keeps a blank line "between two continuation lines" and
makes blank lines "before the first continuation line" inert. For an inline
value, §5.3 calls the first line after `key: first` its "first continuation
line", so a literal reading makes the blank in `k: first\n\n  second` inert.
But User Story 1 scenario 2 keeps the blank in the root scalar
`Para one.\n\nPara two.`, whose first line is not a continuation either.

**Decision**: The blank is **kept**: `k: first\n\n  second` loads as
`{"k": "first\n\nsecond"}`. The rule is stated as "a blank line between two
lines of the same value", where an inline value's text counts as its first
line. Only blank lines before a value's first line (block form: between
`key:` and the first block line), after its last line, or outside any value
are inert.

**Rationale**: It is the one reading consistent with the root case, it is
what an interactive-fiction author writing `- He paused.\n\n  Then he spoke.`
means, and R-03's reconstruction produces it with no special case (the gap is
measured from the inline text's line). `dumps` never writes this shape (it
writes multi-line values in block form, R-05), so the serializer is
unaffected. §5.1, §5.3, and D22 state it explicitly.

**Alternative rejected**: inert, per the literal FR-004 wording. It would need
a special case in R-03 and would make `- He paused.\n\n  Then he spoke.`
silently lose the author's paragraph break.

---

## R-05 — The residual unrepresentable set (Deferred item d; FR-006)

**Decision**: `dumps` keeps its canonical layouts (single-line mapping and
list values inline after one space; every multi-line value, and every root
scalar, in block form with continuation lines two spaces past the marker; a
paragraph break written as an empty line with no indentation). Under those
layouts the unrepresentable set of §11.2.1 is exactly:

1. **Control characters** (rule D, unchanged): `\r`, NUL, and every C0/C1
   control except LF and TAB, at every position.
2. **Structure-shaped first line** at a list position (rule B) or at a block
   position (rule C: any multi-line value, any root scalar). "Structure-shaped"
   is judged by matching the grammar's `structure` rule against the line's own
   characters after its leading spaces, with **no §9.0 pre-processing**, so a
   BOM-led or NBSP-led line is content (FR-006, closes `syml-xreq.6`).
3. **A leading space on the first line** at a mapping or list position. (At the
   root it is kept, FR-005.)
4. **A tab in any line's leading whitespace** (the maximal run of spaces and
   tabs at the start of a line), on any line of the value, at every position.
   On a first line this is "begins with a tab"; on a later line
   (`"a\n  \tb"`) it would trip the §9.0 tab scan. FR-006 listed only the
   first-line case; the later-line case is added. At a mapping position a
   leading tab is also absorbed by FR-008's separator, so `{"k": "\ta"}` is
   unrepresentable for that reason too.
5. **A line that is whitespace-only but not empty**, anywhere in the value
   (`"a\n \nb"`, `"a\n\t\nb"`, the single-line `" "`). §4.4 reads it as blank,
   so it would come back as an empty line. **New; FR-006 missed it.**
6. **A value that begins or ends with an empty line** (`"\nx"`, `"x\n"`,
   `"\n"`): FR-004 makes such blank lines inert.
7. **Keys** outside `[a-z][a-z0-9_-]*`, including `""` (FR-002).
8. **Empty containers** (§11.2.2, unchanged).
9. **A root scalar with a line that begins with `#` or `//`** (added by
   R-18, principal ruling 2026-09-24): at column 0 such a line is a comment,
   so it would be dropped on the way back.

Everything else is written, including every value that was refused only for a
blank, `#`/`//`-led, or structure-shaped *later* line (except at the root:
R-18 adds a ninth item, a root scalar with a line that begins with `#` or
`//`, which would read back as a comment), a BOM- or NBSP-led line
anywhere, and a root scalar with leading spaces.

**Spike evidence**: the round trip `loads(dumps(x)) == x` held for every
accepted value over 5,000 Hypothesis examples (2,450 written, 2,550 refused,
with an alphabet biased toward spaces, tabs, NBSP, BOM, `-`, `:`, `#`, `/`
and newlines). A minimality probe tried every plausible spelling (inline;
block at 2, 3, 4 spaces; inline first line plus block continuation) for each
refused scalar at each position: the only refused values with *any* spelling
were in one family, item 2 at a **mapping** position (see below).

**The one family refused despite having a spelling.** A multi-line mapping
value whose first line is structure-shaped (`{"k": "a: 1\nb"}`) can be written
`k: a: 1\n  b`, because a mapping's inline `data` never re-enters `structure`
(§7.2), and R-01 absorbs the deeper line. `dumps` still refuses it.
Rationale: the inline-first layout has its own restrictions (its second line
sets the baseline, so it may not begin with a space: the spike's first run
failed the round trip on `{"a": "k: \n a"}` for exactly that reason), and it
would make the layout depend on the value's content. FR-006 is normative and
names this family as unrepresentable; User Story 3's narrative ("exactly the
values that have no spelling at all") overstates it by this one family.
§11.2.1 records the inline-first spelling as a v1.x candidate, and the D22
entry mentions it. **Open for the red team**: accepting the family is a
contained serializer change if the principal prefers the narrative's
wording.

**Alternatives considered**: emit inline-first form for that family (above);
emit a whitespace-only line verbatim and accept the lossy read (rejected: §11.2.1's
"MUST raise rather than emit text that would not read back").

---

## R-06 — Text context absorbs a deeper line after an inline value, so three spec examples no longer raise

**Finding**: FR-003 and User Story 1 scenario 16 (`k: first\n  - second\n  key: third`
is one text value) mean *any* line deeper than the owner of an inline value is
that value's continuation. Three places in the spec assumed the 1.0 per-line
lexing instead, and the spike confirms each now loads:

| Input | Spec said | Under FR-003 |
| --- | --- | --- |
| `k:\n  a: 1\n   b: 2` (US2 scenarios 9–10) | `OutOfContextNodeError` at 3:3 | `{"k": {"a": "1\nb: 2"}}` |
| `a: 1\n  - x` (US2 scenario 11) | `OutOfContextNodeError` | `{"a": "1\n- x"}` |
| `parent:\n  child1: value\n   child2: value` (§4.2 invalid example) | `OutOfContextNodeError` | `{"parent": {"child1": "value\nchild2: value"}}` |

The lane-4 notes in `reference/README.md` make the same assumption for
`doc05c_three_space_sibling` (now `{"parent": {"child1": "a", "child2": "b\nchild3: c"}}`)
and `doc05d_item_one_deeper` (now `["milk", "eggs\n- bread"]`).

**Decision**: FR-003 stands (it is the principal's ruling on `syml-xreq.22`,
restated by US1 scenario 16). The error scenarios get inputs that still raise
and still exercise the same message machinery; the spec, §4.2, and the
reference README are corrected in the plan commit:

- US2 scenario 9: `k:\n  a: 1\n b: 2` → `str(error)` is `3:1: <message>` then
  ` b: 2`; the message states line 3 is at column 1 while the open blocks are
  at columns 0 and 2.
- US2 scenario 10: the same document with `filename="f.syml"` → `f.syml:3:1: `.
- US2 scenario 11: `a: 1\n- x` (a list item at a mapping's level) replaces
  `a: 1\n  - x`.
- §4.2's invalid example becomes the one-space dedent (`parent:\n  child1: value\n child2: value`),
  and the three-space line is shown as the text continuation it now is.

**Cost, recorded in D21**: a line indented one or more spaces past a sibling
key that holds an inline value is silently absorbed into that value instead of
raising. This is exactly the hazard D13 rejected ("silently absorbs
`key: v\n  nested: x`, a likely authoring error"); the ruling on `syml-xreq.22`
accepted it in exchange for text that is never reinterpreted. The README's
"Coming from YAML" section does not list it (it is not a YAML habit); D21's
breaking-change note and CHANGELOG do. **Flagged for the principal** in the
plan's open questions: this is the one place the new rule is quieter than the
old one.

---

## R-07 — `str(ParseError)` without a doubled filename (FR-011, FR-013)

**Finding**: FR-013 puts the filename in `.message` (`f.syml: Duplicate key`)
and FR-011 wants `str(e)` to read `f.syml:3:1: <message>`. Formatting
`<filename>:<line>:<col>: <message>` from `.message` yields
`f.syml:3:1: f.syml: …`, and US2 scenario 10 requires `str(error)` to begin
`f.syml:3:1: ` and `.message` to begin `f.syml: `.

**Decision**: `ParseError.__init__(message, position, line_text, *extra, filename=None)`.
`message` is the bare description. The constructor stores it privately as
`_description`, stores `_filename` (an empty string normalizes to `None`,
FR-013), and sets the public `.message` to `error_message(description, filename)`.
`__str__` returns `f'{loc}: {self._description}\n{self.line_text}'`, where
`loc` is `f'{filename}:{line}:{column}'` or `f'{line}:{column}'`, from
`self.position` (§10.2: 1-indexed line, 0-indexed column).

No new public attribute (FR-011). `.args` remains
`(message, position, line_text, *extra)` with the prefixed `.message` first,
so existing `e.args[1]` callers keep working. Pickling stays correct without a
custom `__reduce__`: `BaseException.__reduce__` returns `(cls, args, __dict__)`,
so `cls(*args)` rebuilds the object and the `__dict__` update restores
`_description` and `_filename` (a test pins the pickle round trip of `str(e)`).

Every raise site passes `filename=` rather than prefixing by hand:
`Mapping.can_add_node` (`DuplicateKeyError`), the Root failure path
(`OutOfContextNodeError`), the tab scan (`TabIndentationError`), and
`encoding_error` (`EncodingError`). `error_message` also treats `""` as no
filename, so `filename=''` stops yielding `': Duplicate key'`.

**Alternatives considered**: partition `.message` on the first `': '`
(rejected: a filename or description may contain `': '`); a public
`.filename`/`.description` attribute (rejected by FR-011's "no new
attribute"); dropping the prefix from `.message` (rejected by FR-013 and
CHANGELOG item 9).

---

## R-08 — Where the open columns and hints come from (FR-012)

**Decision**: Everything the message needs is computed at the point of
failure, on `Root`, with no builder plumbing:

- **Open columns.** The tip is always the last descendant of `Root` (every
  `add_node` returns the new subtree's tip, and the tip only moves down the
  rightmost spine). So `Root.fail_to_incorporate_node(node)` walks
  `children[-1]` from itself to the leaf and collects the levels of the `List`
  and `Mapping` nodes on that spine: the columns at which a sibling line would
  have been accepted. For `k:\n  a: 1\n b: 2` that is `0, 2`.
- **The line above** is the nearest earlier line of the normalized text that
  is neither blank nor a column-0 comment (from `node.pnode.full_text`), not a
  node (R-18 added the comment clause).
- **Hint (a), would-be key.** Fires when the failing line, or the line above
  it, has the shape `<run>:` followed by a space, a tab, or end of line, where
  `<run>` is a non-empty run of non-whitespace, non-colon characters after the
  indentation spaces that does **not** match `[a-z][a-z0-9_-]*`
  (`firstName:`, `URL:`, `Given:`, `e.mail:`).
- **Hint (b), list at its key's column.** Fires when the failing node is a
  `ListItem` and the spine ends in a childless `KeyValue` at the same level
  (`k:\n- a`, `- key:\n  - x`).

Message shape (exact wording pinned in Contract 03; "does not fit" rather
than "matches no column", because a list item at an open mapping's column is
at an open column but still has no place; that case gets its own sentence
naming the kind mismatch, see Contract 03):

```text
Line 3, at column 1, does not fit any open block; open blocks are at columns 0 and 2.
```

with an optional trailing sentence, one of:

```text
Hint: 'firstName' is not a key; a key is lowercase ASCII letters, digits, '-' and '_', starting with a letter.
Hint: a list under a key must be indented past the key's column.
```

**Alternatives considered**: carry the walk-up chain on the exception from
`_delegate_incorporate_node` (rejected: the rightmost spine gives the same set
without threading state through every `incorporate_node`); a `reason` code or
`expected_columns` attribute (rejected by the ruling on `syml-xreq.18`).

---

## R-09 — Tab-scan positions and the BOM as a code point (FR-013; US2 scenarios 12–13)

**Finding**: §10.2 does not say whether the BOM counts toward column and
index. `PositionMap.to_original` already adds `bom_offset` to `index` and, on
line 1, to `column`, so every other error already counts the BOM as a code
point of the original text. US2 scenarios 12–13 assume the same.

**Decision**: The BOM counts. §10.2 gains one sentence: positions are
code-point offsets into the caller's original text, so a stripped BOM still
occupies index 0 and column 0 of line 1. The fix is ordering: `preprocess`
builds the `PositionMap` before `_scan_for_tab_indentation`, passes it and
the filename into the scan, and routes the scan's `Pos` through
`PositionMap.map`. Checks: `a: 1\r\n\tb: 2` → index 6, line 2, column 0;
`\ufeff\tk: v` → index 1, line 1, column 1; `\ufeffa: b\r\n\tc: d` →
index 7, line 2, column 0.

---

## R-10 — The FR-017 tail

- **§11.3.** `EncodingError(ParseError)` is listed. `DocumentLimitError` moves
  from the MUST list to a paragraph reserving the name for implementations that
  enforce §13.4; `syml` enforces no limit and does not export the name. The
  "MUST expose these exact class names" sentence then covers exactly the
  classes `syml` exports, and a test compares §11.3's list with
  `syml.__all__`'s exception names.
- **`dumps('')`** returns `''` (the empty document, rule A). `dump('')` writes
  `''`. The trailing-newline convention applies only to non-empty output.
- **Input type guards.** `loads(document)` raises
  `TypeError("loads() expects str, not bytes")` (type name interpolated) for
  any non-`str` document. `load` accepts a `read()` result of `str` or
  `bytes`; anything else is `TypeError`. A `ValueError` raised by `read()`
  itself that is not a `UnicodeDecodeError` (a closed handle's
  `I/O operation on closed file`) is re-raised as `TypeError(...) from err`,
  so `except ValueError` (and therefore `except ParseError`'s base) never
  catches an I/O fault as a parse error. The spec's Edge Cases ask for
  `TypeError` here; it is an odd class for a closed file, but the alternative
  (let `ValueError` through) is the confusion `syml-xreq.13` reports.
- **Filename from `.name`.** `_resolve_filename` accepts `str` and any
  `os.PathLike`; a `Path` passes through, any other `os.PathLike` becomes
  `os.fsdecode(os.fspath(name))`. A `bytes` name and an `int` (file
  descriptor) name are ignored, as today (not required by FR-017; YAGNI).
- **Blank-only document `Source`.** `Pos.from_str_index` at an index just
  past a trailing `\n` reports the next line, column 0 (`parse('\n')` →
  `Pos(index=1, line=2, column=0)`), so line and column agree with the index.
  `syml-xreq.11`'s original input `# x\n` is zero-width again under R-18's
  column-0 comment rule, so the same fix covers it:
  `parse('# x\n').as_source().start` is `Pos(index=4, line=2, column=0)`.

---

## R-11 — FR-008 changes two more 1.0 examples

**Finding**: With `ws = ~"[ \t]+"`, the separator absorbs every space and tab
after the marker, so a tab can no longer be the first character of an inline
value:

- §7.5 `key: \tv` → was `{"key": "\tv"}`, now `{"key": "v"}`.
- §9.3 "`key: \t` has the one-character value `\t`" → now the bare marker
  (`key:` then a block, or `""`).
- §4.2 rule 3's `key: \tv` sentence goes; a value that begins with a tab is
  unrepresentable because it cannot be written, not because it is confusing.
- §7.5 `key:\tv` → was `"key:\tv"` (root scalar), now `{"key": "v"}`; §7.6's
  table row for it changes the same way.

The ruling on `syml-xreq.19` said "nothing valid today changes meaning"; that
is true of the tab directly after the marker but not of a tab after a
separator space. D24 records the `key: \tv` change as part of its
breaking-change note. Contract 06 §A lists every flipped example so the
spec-example oracle (SC-005) is updated in the same leaf.

---

## R-12 — A root scalar's leading indentation and its `Source` (FR-005)

**Decision**: When `Root` accepts its first child and that child is a text
line, the builder rebuilds it over the **whole line** (from column 0,
indentation included) with level 0, and `Root` fixes its baseline at 0. The
leading spaces are then part of the first line's text, and later lines keep
their indentation beyond column 0 through the existing D11 arithmetic. The
root scalar's `as_source().start` is line 1, column 0 (after a BOM, column 1:
R-09). No change for mapping or list roots.

**Spike evidence**: `  hello`, `  hello\nworld`, `  hello\n    world` give the
ruled values; `doc03b_prose_root` loads as its author wrote it.

**Alternative rejected**: keep the leaf's span after the indentation and
prepend `' ' * (level - baseline)` in `as_data`. Equivalent data, but `as_source().text` would no longer equal the
source slice for a one-line indented root scalar, and the prefix arithmetic
would need a root-only branch in `as_data`.

---

## R-13 — `bar.syml` has two same-column lists, not one (FR-010, SC-003)

FR-010 names lines 23–24 (`  - when:` / `    - Bar >= 2`). Lines 35–36
(`  - effect:` / `    - Location = "Foyer"`) are the same shape and also
raise under strict indentation (spike: `OutOfContextNodeError` at line 36).
Both pairs are re-indented by two spaces; the spike confirms the fixture then
loads to a tree identical (JSON-equal) to today's. The spec's FR-010 is
corrected in the plan commit.

---

## R-14 — Tooling for SC-002 and SC-005

- **Round-trip property.** `reference/lane-1-roundtrip-probe.py` becomes
  `tests/test_roundtrip_property.py`: properties P1 (round trip), P2 (contract
  exceptions only), P3 (loads raises only `ParseError`/`RecursionError`),
  P4 (`as_source` agrees with `as_data`), P5 (line-ending and BOM invariance),
  and P7 (key predicate equals `[a-z][a-z0-9_-]*`). `FILTER_KNOWN` and
  `known_family` are deleted; `valid_key` becomes
  `st.from_regex(r'[a-z][a-z0-9_-]*', fullmatch=True)`; `SEED_STARTS` keeps its
  NBSP, BOM, and Unicode-space seeds (they must now round-trip or be refused
  cleanly) and gains paragraph-break and structure-shaped later-line seeds. The
  `signal.alarm` timeout is dropped (pytest has its own; `alarm` is not
  portable). Example counts are kept modest (a few hundred per property) so the
  unit suite stays fast; the hardening phase may raise them.
- **Hypothesis** joins the `test` dependency group. It is not a runtime
  dependency, so constitution principle V's gate does not apply; the plan's
  Complexity Tracking records it anyway for visibility.
- **Spec-example oracle.** `tests/test_spec_examples.py` already extracts and
  runs every `**Output:**`/`**ERROR:**` example; it is kept, and
  `MINIMUM_EXAMPLE_COUNT` moves to the count after the spec edit. No second
  extractor is written.
- **Grammar diff.** A new test in `tests/test_spec_examples.py` performs R-02's
  rule-by-rule comparison of §4.1 against `SymlParser.grammar`.
- **Lane-4 documents.** The four SC-004 documents are copied into
  `tests/fixtures/lane4/` with their ruled values pinned in a test; the other
  30 stay reference material.

---

## R-15 — The 24 repros at the branch point

Re-run on `002-syml-language-revision` at `3bda444` (no `src/` or `tests/`
change since `27a3e9a`). Every one still reproduces:

| Issue | Observed at `3bda444` |
| --- | --- |
| `.1` | `\xa0k: v` → `{'k': 'v'}`; `\u2028- x` → `['x']`; NBSP-only line swallowed; `\x0bx` → `'x'`; `\x0c` → `''`; `\xa0\tx` → `'x'` |
| `.2` | `  hello` → `'hello'`; `  hello\nworld` → `OutOfContextNodeError`; `dumps('  hello')` refused |
| `.3` | `k:\n- a\n- b` → `{'k': ['a', 'b']}`; `- key:\n  - x` → `[{'key': ['x']}]` |
| `.4` | `OutOfContextNodeError`/`TabIndentationError` `.message` unprefixed; `filename=''` → `': Duplicate key'` |
| `.5` | tab-scan `Pos` index 5 (the `\n`) and index 0 (the BOM) |
| `.6` | `dumps(['\ufeff- x'])` and `dumps({'k': 'a\n\ufeff- x'})` refused |
| `.7` | `hasattr(syml, 'DocumentLimitError')` is `False` |
| `.8` | `SymlParser().parse('a: 1')` works (CHANGELOG 12 says otherwise) |
| `.9` | `.message` is `'Duplicate key'` (§8.3 shows `Duplicate key 'key'`) |
| `.10` | trailing-line walk-up: `RecursionError` at 250 levels, fine at 240 |
| `.11` | `parse('# x\n').as_source().start` is `Pos(index=4, line=1, column=0)` |
| `.12` | `dumps('')` → `'\n'` |
| `.13` | `loads(b'k: v')` leaks a `startswith` `TypeError`; closed handle leaks `ValueError` |
| `.14` | `PurePosixPath` `.name` ignored |
| `.15` | paragraph breaks dropped |
| `.16` | `- [ask: why?]` → `[{'[ask': 'why?]'}]` (and the other three) |
| `.17` | `env:\n  HOME: /h` silent text; `firstName` blames line 2 with no hint |
| `.18` | `str(e)` is the args tuple |
| `.19` | `k:\tv` → text; `a:\t` blames the next line |
| `.20` | `- server:\n  host: x` → `[{'server': '', 'host': 'x'}]` (ruled: keep) |
| `.21` | `#`/`//` continuation lines dropped |
| `.22` | dash-led continuation raises |
| `.23` | `dumps(parse('k: v').as_source())` → `TypeError` |
| `.24` | `key: \|` literal; `---\nk: v` raises |

---

## R-16 — The ready-queue hazard (recorded for `/sp:05-tasks`)

`br dep tree syml-s9p9 --direction up` returns all 24 `syml-xreq` children,
because the epic links them with `related` edges, so the ralph drain's
`prep.sh` would treat each bare child as a ready leaf task. `/sp:05-tasks`
MUST do one of the following for every child: add a `blocks` dependency from
the child on the task that pins it (so the child is never ready before its
test exists), or have the pinning task close the child from inside and exclude
`syml-xreq.*` from the drain's candidate set. It must not leave a bare child
claimable. The mapping from child to pinning contract is in plan.md
§ Spec Conformance.

---

## R-17 — Measuring the recursion cliff for CHANGELOG item 13 (`syml-xreq.10`)

The walk-up stays recursive (Scope Boundaries). The grammar change alters
Parsimonious's recursion profile, so CHANGELOG 13's figures are measured
**after** the grammar leaf lands, at CPython's default limit, for four cases:
block nesting with no trailing line, block nesting followed by a line that
climbs to the top (the `syml-xreq.10` repro), inline `- - … x` nesting, and
`dumps` of nested data. The release-text leaf states the measured numbers and
the `parse()`-succeeds/`as_data()`-raises split at depth, rather than the
current "~500"/"~1,000" claims, together with the existing "scales with
`sys.getrecursionlimit()`" wording. The figures are not pinned by a test:
recursion depth under pytest depends on the runner's own stack and the
Python version, so an exact assertion would be flaky. The measurement method
(the four cases above, bisected at the default limit) is recorded in the
release-text contract so it can be repeated before any future tag.

---

## R-18 — Comments at column 0 (principal ruling, 2026-09-24; plan open questions 7–9)

**Ruling**: A line whose first character, at column 0 with no indentation,
is `#`, or whose first two characters are `//`, is a comment. It is skipped
as if it were not in the document, anywhere in the document, including
between two lines of an open text value, where it is not a paragraph break.
Every indented `#`/`//` line, and every `#` after a key or marker, stays
ordinary text. This supersedes the "remove comments entirely" reading of
`syml-xreq.21` that FR-007 and D23 recorded. Open question 8 is resolved by
the same ruling (no new hint), and open question 9 is ruled "document only".

**Decision (mechanism)**: a grammar alternative, not pre-processing.

```peg
line    = comment / (indent (structure / data))
comment = ~"(?:#|//)[^\n]*"
```

- **Column 0 falls out of PEG order.** `line` tries `comment` first, at the
  line's first character. An indented line starts with a space, so
  `comment` fails and the `indent` branch runs; the `#` is then lexed as
  `data`, exactly as the plan already treats it. No lookbehind and no
  indentation test is needed.
- **The parentheses are required.** Parsimonious's rule grammar does not
  parse `comment / indent (structure / data)` (an `IncompleteParseError` at
  the `(`); `comment / (indent (structure / data))` loads, and its
  `as_rule()` is `comment / (indent (structure / text))`. §4.1 prints the
  parenthesized form so the identity test compares like with like.
- **One regex, no `text` child.** `comment` is a single regex rather than
  `("#" / "//") text`, so `visit_text` never builds a `TextLeafNode` for a
  comment's content only to have it discarded.
- **The visitor drops the line.** `visit_comment` returns `None`, and
  `visit_line` returns `None` when the chosen alternative is `comment`
  (`node.children[0].expr_name == 'comment'`), the same path a blank line
  takes. No `Comment` node, no `comments` list, and nothing reaches the tree
  builder, so every later line keeps its own parse node and its own
  original-text position.
- **The BOM.** §9.0 strips one BOM at index 0 before lexing, so
  `\ufeff# header` is a comment, and a later position still counts the BOM
  as index 0 of the original text (R-09). A BOM anywhere else is content, so
  `a: 1\n\ufeff# x` is a text line at a mapping's column and raises.
- **The tab scan.** A column-0 comment's leading run of spaces and tabs is
  empty, so §9.0's tab scan never fires on it, and a tab after the marker
  (`#\tx`) is comment content.

**Blank-line count (fixes R-03's formula).** R-03 counted every line break
in the gap between two lines of a value
(`full_text[prev.pnode.end : node.pnode.start].count("\n") - 1`). That
counts a comment line as a blank line, so `k:\n  a\n# n\n  b` would load as
`{"k": "a\n\nb"}`, which the ruling forbids. The count is now over the
blank lines in the gap only:

```python
gap = full_text[prev.pnode.end : node.pnode.start]
node.blank_lines_before = sum(1 for line in gap.split("\n")[1:-1] if preprocess.is_blank(line))
```

`[1:-1]` drops the tail of `prev`'s line (empty, since a text leaf ends at
its line's end) and the indentation of `node`'s own line. Every line left is
blank or a column-0 comment (any other line would have joined the value or
ended it), so counting blanks is the same as not counting comments, and it
reproduces R-03's whitespace-only row (`k:\n  a\n      \n  b` →
`{"k": "a\n\nb"}`).

**Blank lines on both sides of a comment.** The ruling says a comment is
skipped "as if it were not there". Read literally, deleting the line leaves
both blank lines, and FR-004 keeps each physical blank line: so
`k:\n  a\n\n# note\n\n  b` is `{"k": "a\n\n\nb"}` (two empty lines), and
`k:\n  a\n\n# note\n  b` is `{"k": "a\n\nb"}`. No coalescing rule is added.

**Serializer.** A root scalar is written in block form at column 0, so a
line of it that begins with `#` or `//` would read back as a comment and be
dropped. It has no other spelling (a root scalar's baseline is column 0;
indentation would become part of the value), so Contract 04 adds item 9: a
root scalar with any line that begins with `#` or `//` is
`UnrepresentableValueError`. No other output can put `#` or `/` at column 0:
a key matches `[a-z]…`, a list line starts with `-`, a paragraph break is an
empty line, and every non-root value is indented at least two spaces. A
value that begins with a BOM and then `#` is still written: the output's
extra BOM (unchanged rule) means `loads` strips one and keeps `\ufeff# x`
as content. **No new load-only family**: `loads` never returns a root scalar
with such a line, because such a line is a comment.

**Spike evidence** (the planning spike copied to the session scratchpad with
the three changes above):

- `check.py`: 70 inputs, 5 mismatches, all expected: the three rows R-06 made
  text and US1-14's two pre-ruling values.
- A 36-input table (every new US1 scenario, 19–27, plus edge rows) gives the pinned
  output, including `#\tx`, `//\tx`, `/x`, `///x`, `#!/bin/sh`, `\xa0# x`,
  `a:\n  b: 1\n# note\n  c: 2`, `- a\n# note\n- b`, and `k: v\n# c\n  more`.
- Positions after a comment are the original text's: `a: 1\n# c\n- x`
  raises at `Pos(9, 3, 0)`; `\ufeff# c\r\n\tb` raises `TabIndentationError`
  at `Pos(4, 2, 0)`.
- `check2.py`: the lane-4 documents change only where the ruling says:
  `doc02_config` loads as a mapping (its `# Application config` header is a
  comment), `doc09c_only_comments` loads as `"  # three"`, and
  `doc09g_comment_no_nl` as `""`.
- `fuzz.py` (5,000 examples, an alphabet with `#`, `/`, and newlines):
  every accepted value round-trips; the refused-but-spellable probe finds
  only family L1.
- A load-first run (20,000 generated documents of column-0 and indented
  `#`/`//` lines, markers, keys, NBSP, BOM, VT, and tabs): every loaded
  value either round-trips through `dumps` or is refused for an L1/L2
  value; `dumps` never writes a line that begins with `#` or `//`; and
  `loads(t)` equals `loads` of `t` with its column-0 comment lines deleted.

**One surprise**: the deletion equivalence needs one qualifier. §9.0 strips
a BOM only at index 0 of the original text, so `# c\n\ufeffz` loads as
`"\ufeffz"`, while `\ufeffz` alone loads as `"z"`. The comment does not move
the start of the document. The property therefore deletes comment lines
from the text after the index-0 BOM strip; spec.md Edge Cases states the
exception.

**Hints.** Contract 03's hint (a) reads "the line above" from the normalized
text. It now skips column-0 comment lines as well as blank lines, so
`config:\n  Host: x\n# c\n port: 1` still names `Host`. The failing line
itself can never be a comment.

**Alternatives considered**:

- *`#` alone* (drop `//`). Not taken: the principal chose both markers, as
  0.6.2 and the 1.0 draft had them.
- *Comments only between structure entries* (a column-0 comment inside an
  open text value would be text, or would end the value). Not taken: the
  principal chose "anywhere". It would also make a comment's meaning depend
  on the builder's state, which the per-line lexing rule avoids.
- *Pre-processing removal* (delete comment lines before parsing, or blank
  them out). Not taken. Deleting lines shifts every later position and needs
  a second position map. Blanking them keeps positions but turns each
  comment into a blank line, so R-03 would count it as a paragraph break.
- *A lookbehind in `comment`* (`~"(?<![ ])(?:#|//)…"` inside
  `indent (comment / structure / data)`). Not taken: PEG order already
  gives column 0 with no regex trick.
- *Keep D23 ("no comments")*. Overruled by the principal (plan open
  question 7): its premise that every consequence is loud was false, and a
  0.6.2 file header silently turned the whole file into one string.
