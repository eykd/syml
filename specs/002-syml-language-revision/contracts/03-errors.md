# Contract 03 — Error Text, Hints, Filenames, and Positions

**Requirements**: FR-011, FR-012, FR-013, FR-016 (§8.3 example) | **Decisions**: D7 affirmed (one class for §8.1/§8.2) | **Findings closed**: `syml-xreq.4`, `.5`, `.9` (§8.3 half), `.17` (hint half), `.18`, `.3` (hint half) | **Research**: R-07, R-08, R-09, R-18

## Surface

```python
class ParseError(ValueError):
    message: str        # prefixed with '<filename>: ' when a filename is known
    position: Pos       # original-text coordinates (§10.2)
    line_text: str

    def __init__(
        self,
        message: str,              # the bare description
        position: Pos,
        line_text: str,
        *extra: object,
        filename: StrPath | None = None,
    ) -> None: ...

    def __str__(self) -> str: ...

def error_message(description: str, filename: StrPath | None) -> str: ...
```

Private state: `_description: str`, `_filename: str | None` (`""`
normalizes to `None`; a `PathLike` is normalized with `os.fspath`, so
`loads(text, filename=PurePath("p.syml"))` and `load()`'s `.name` give the
same prefix). No new public attribute. `.args` is
`(self.message, position, line_text, *extra)`.

`__str__`:

```text
<filename>:<line>:<column>: <description>
<line_text>
```

The `<filename>:` part is omitted when there is none. `<line>` is 1-indexed,
`<column>` 0-indexed (§10.2), both from `self.position`.

**Rendered, not echoed** (red team pass 1, plan § Security Considerations):
`__str__` passes `<line_text>` through a private `_printable(text)` helper
that replaces each character for which `str.isprintable()` is false with its
Python escape (`repr(ch)[1:-1]`: `\t`, `\x1b`, `\xa0`, `\u202e`, `\x00`).
Hint (a) interpolates its would-be key through the same helper when the
description is built, so the escaped key is part of `.message` too. The
`<filename>` segment of `__str__` goes through `_printable` as well (red team
outer iteration 3): a filename is caller- or attacker-controlled (archive
entry names), a `\n` in it would break `str(e)`'s two-line shape, and
`load()` on a handle whose `.name` is an undecodable `bytes` path yields lone
surrogates (`'\udcff.syml'`), which make `print(e)` raise
`UnicodeEncodeError` on a UTF-8 stream. Apart from those, `.line_text`,
`.message` (including its filename prefix), and `.args` carry the raw text. `<column>` still counts code points of the
raw line, so it is not a caret offset into the rendered text (there is no
caret).

**Bounded rendering** (`syml-s9p9.9`): `_printable` can expand a single
character to several (`'\x00'` renders as the 4 characters `\x00`), so
attacker-controlled text is windowed through a private
`_truncated_window(text, *, center, width=80)` helper *before* escaping —
capping the pre-escape window bounds the escaped output too, regardless of
how long the hostile input is. `__str__` windows `<line_text>` centered on
`<column>`; hint (a) windows its would-be-key quote centered on `0` (the run
always starts at the candidate key's own first character). A truncated side
is marked with a single `'…'`. Neither `.line_text` nor `.args` is affected —
only `__str__`'s rendering and hint (a)'s quoted run inside `.message` are
windowed — so a 1 MB hostile line (e.g. a run of `\x00` before a bare `:`)
still yields a bounded `.message` and `str(e)` instead of the unbounded,
multi-megabyte rendering this caps.

## Messages

| Class | Description (the part after any filename prefix) |
| --- | --- |
| `OutOfContextNodeError` | When `C` is not an open column: `Line {L}, at column {C}, does not fit any open block; open blocks are at {COLS}.` When `C` is an open column whose block holds the other kind of entry (§6.4): `Line {L}, at column {C}, is a {KIND}, but the open block at column {C} holds {OTHER}; open blocks are at {COLS}.` (`KIND`/`OTHER` from `list item`/`keys`, `key`/`list items`, `text line`/`keys` or `list items`). Either form is optionally followed by the text-value clause (below), then by one space and a hint |
| `DuplicateKeyError` | `Duplicate key '{key}'` (unchanged attributes `key`, `first_position`) |
| `TabIndentationError` | `A tab character was found in a line's leading whitespace` (unchanged) |
| `EncodingError` | `Invalid encoding` (unchanged) |

`{COLS}` is `column 0` for one column, `columns 0 and 2` for two,
`columns 0, 2 and 4` for more: the sorted distinct levels of the `List` and
`Mapping` nodes on `Root`'s rightmost spine at the time of failure (R-08). The spine walk follows `children[-1]` from `Root` and **stops at the first
`TextLeafNode`** (the open value, the builder's tip): a text value's
continuation lines are its `TextLeafNode` children, and `get_tip()` would
descend into them and return the last continuation, which the gate below
must not mistake for the value's first line (red team outer iteration 6).
"Previous non-blank line" and every other blankness test on the failure path
use `preprocess.is_blank` (spaces and tabs only), never `str.strip()`, so a
NBSP-only continuation counts as a line (FR-009). The previous line also
skips column-0 comment lines (FR-007, principal ruling 2026-09-24): "the
line above" is the nearest earlier line that is neither blank nor a line
whose first character is `#` or whose first two are `//`. The failing line
itself is never a comment, because the visitor drops a comment line before
the builder sees it. The
list is never empty: `Root` can only fail once its first child is a `List` or
`Mapping` (a root scalar absorbs every later line).

**Text-value clause** (red team outer iteration 2; FR-012's "every column
that was open during the walk-up"): when the spine ends in a `TextLeafNode`
whose `baseline` is set (a block value, or an inline value that already has a
continuation) and the failing column is below that baseline, the sentence's
final `.` becomes `; the open value continues at column {B}.`, where `{B}` is
the baseline. The walk-up started at that value, and its baseline is the
column a prose author most likely meant; without the clause
`k: a\n    b\n  c` would name only column 0. An inline value with no
continuation yet (baseline unset) gets no clause: its anchor column is
already in `{COLS}` (US2-9 keeps its exact text).

Hints (at most one; (b) is checked first):

- **(b) list at its key's column**: the failing node is a `ListItem` and the
  spine ends in a childless `KeyValue` at the same level →
  `Hint: a list under a key must be indented past the key's column.`
- **(a) would-be key**: the failing line, or the previous non-blank line,
  after its indentation spaces, is `RUN:` followed by a space, a tab, or end of
  line, where `RUN` is a non-empty run of characters that are neither
  whitespace nor `:` and does not fully match `[a-z][a-z0-9_-]*` →
  `Hint: 'RUN' is not a key; a key is lowercase ASCII letters, digits, '-' and '_', starting with a letter.`
  **Gating** (red team outer iteration 2): a would-be-key line qualifies only
  where lowercasing it could make it a key that fits. The **failing line**
  qualifies only when its column is one of `{COLS}` that holds keys (an open
  `Mapping` column); the **line above** qualifies only when it is the first
  line of the value at the tip of the spine (the line whose text-ness opened
  the text context, i.e. a bare block's first line; a root scalar never fails),
  not a later continuation line or an inline value's line, **and** only when
  the failing node is a `KeyValue` or `ListItem` (the failing line lexed as
  structure, so the author was writing structure there; red team outer
  iteration 7). Without the gate, dialogue in a prose value
  (`- scene:\n    Bob: hi\n    Carol: yo\n   Alice: hey`) gets
  `'Alice' is not a key`, which names the wrong fix for a one-space dedent;
  without the failing-node clause, the same dialogue with one line before the
  dedent (`- scene:\n    Bob: hi\n   Alice: hey`) gets `'Bob' is not a key`,
  because `Bob: hi` is the value's first line.

## Behaviour

| # | Input (`filename`) | Result |
| --- | --- | --- |
| US2-1 | `k:\n- a\n- b` | `OutOfContextNodeError`; description `Line 2, at column 0, is a list item, but the open block at column 0 holds keys; open blocks are at column 0. Hint: a list under a key must be indented past the key's column.` |
| US2-9 | `k:\n  a: 1\n b: 2` | `str(e) == "3:1: Line 3, at column 1, does not fit any open block; open blocks are at columns 0 and 2.\n b: 2"` |
| US2-10 | same, `"f.syml"` | `str(e)` begins `f.syml:3:1: `; `e.message` begins `f.syml: ` |
| US2-11 | `a: 1\n- x` and `a:\n\tb`, `"f.syml"` | both `.message` begin `f.syml: ` |
| US1-8 | `name: a\nfirstName: b\nage: 3` | raises at line 2; hint (a) names `firstName` |
| US2-12 | `a: 1\r\n\tb: 2` | `TabIndentationError`, `position == Pos(6, 2, 0)` |
| US2-12 | `\ufeff\tk: v` | `TabIndentationError`, `position == Pos(1, 1, 1)` |
| US2-13 | `\ufeffa: b\r\n\tc: d` | `TabIndentationError`, `position == Pos(7, 2, 0)` |
| FR-013 | `a: 1\na: 2`, `""` | `.message == "Duplicate key 'a'"` (no `": "` prefix) |
| SC-007 | a plain context error (`a: 1\nb`) | `str(e)` line 1 is `2:0: …` with no hint; line 2 is `b` |
| text clause | `k: a\n    b\n  c` (US1-18) | description `Line 3, at column 2, does not fit any open block; open blocks are at column 0; the open value continues at column 4.` |
| text clause | `k:\n  a\n\xa0\n  b` (US2-7) | description `Line 3, at column 0, is a text line, but the open block at column 0 holds keys; open blocks are at column 0; the open value continues at column 2.` |
| gate | `- scene:\n    Bob: hi\n    Carol: yo\n   Alice: hey` | no hint (column 3 is not an open `Mapping` column; `Carol: yo` is a continuation, not the value's first line); description ends `; the open value continues at column 4.` |
| gate | `config:\n  Host: x\n port: 1` | hint (a) names `Host` (the line above is the first line of `config`'s block value, and the failing line `port: 1` lexed as a key) |
| gate | `- scene:\n    Bob: hi\n   Alice: hey` | no hint (the failing line lexed as text, so the line above does not qualify even though it is the value's first line); description `Line 3, at column 3, does not fit any open block; open blocks are at columns 0 and 2; the open value continues at column 4.` (red team outer iteration 7) |
| gate | `config:\n  Host: x\n# c\n port: 1` | hint (a) names `Host` (the column-0 comment between them is skipped when finding the line above; R-18) |
| position | `a: 1\n# c\n- x` | raises at `Pos(9, 3, 0)`; description `Line 3, at column 0, is a list item, but the open block at column 0 holds keys; open blocks are at column 0.` (the dropped comment line keeps its number, so line numbers are the original text's) |
| gate | `config:\n  Host: x\n Port: 1` | no hint (the failing line lexed as text; column 1 is not an open `Mapping` column, so it does not qualify on its own either) |
| punctuation key | `a: 1\nbooleans?: x` | description `Line 2, at column 0, is a text line, but the open block at column 0 holds keys; open blocks are at column 0. Hint: 'booleans?' is not a key; a key is lowercase ASCII letters, digits, '-' and '_', starting with a letter.` (the README's former lead-example key; US1-8 covers only camelCase, red team outer iteration 4) |
| escape | `k:\n  a\n\xa0\n  b` | `str(e)`'s second line is `\\xa0` (the four characters backslash, `x`, `a`, `0`); `e.line_text == "\xa0"` |
| escape | `a: 1\n\x1b[31mX: y` | `str(e)` contains no `\x1b` character; its second line is `\\x1b[31mX: y`; hint (a) names `'\\x1b[31mX'` |
| escape | `a: 1\na: 2`, `filename="x\n\x1b[2J\udcff.syml"` | `str(e)` is exactly two lines; its first begins `x\\n\\x1b[2J\\udcff.syml:2:0: ` (escaped); `str(e).encode("utf-8")` does not raise; `e.message` begins with the raw filename |
| filename | `a: 1\na: 2`, `filename=pathlib.PurePosixPath("p.syml")` | `str(e)` begins `p.syml:2:0: `; `e.message` begins `p.syml: ` |

## Placement

- `Root.fail_to_incorporate_node(node)` builds the OutOfContext description,
  the hint, the original-text `Pos` (through `PositionMap.map`, as today), and
  raises with `filename=self.filename`. `SymlNode.fail_to_incorporate_node`
  keeps a minimal fallback only if a non-`Root` node can reach it; if none can,
  it is removed rather than left uncovered (principle III).
- `Mapping.can_add_node` raises `DuplicateKeyError(f"Duplicate key {key!r}", ..., filename=node.filename)`.
- `preprocess` builds the `PositionMap` first and passes it and `filename` to
  `_scan_for_tab_indentation`, which maps its `Pos` (R-09).
- `encoding_error` passes `filename=` instead of calling `error_message`.
- §10.2 gains: positions are code-point offsets into the caller's original
  text; a stripped BOM still counts as index 0 / column 0 of line 1.

## Test obligations

1. Every row above.
2. `str(e)` for each of the four `ParseError` subclasses, with and without a
   filename, with `filename=""`, with a `PurePosixPath` filename, and with a
   filename containing `\n`, `\x1b`, and a lone surrogate (the escape rows).
3. `pickle.loads(pickle.dumps(e))` preserves `str(e)`, `.message`, `.args`,
   and (for `DuplicateKeyError`) `.key` / `.first_position`.
4. The column list formatter: one, two, and three columns; both message forms
   (column not open; open column of the other kind, incl. `- item\nkey: value`
   and `a:\n  b: 1\n  plain`).
5. The text-value clause: present for a block value and for an inline value
   with a continuation (US1-18, US2-7); absent for an inline value without one
   (US2-9's exact `str(e)` is unchanged) and when the spine ends in a
   container.
6. Hint (a) fires on the failing line and on the line above; does not fire for
   `a: 1\nb` or for a line whose colon is followed by a non-space; does not
   fire from the line above when the failing line lexed as text (the two
   outer-iteration-7 gate rows); hint (b)
   fires for `k:\n- a` and `- key:\n  - x`, not for `k:\n  - a\n- b`.
7. SC-007's three cases as acceptance scenarios (US11).
8. `_printable`: `str(e)` contains no character outside `str.isprintable()`
   except the one `\n` between its two lines, for every raised error in the
   SC-002/P3 property run (the property asserts it on each `ParseError`).
9. Bounded rendering (`syml-s9p9.9`): a hostile 1 MB line (e.g. a run of
   `\x00` before a bare `:`) yields a `.message` and `str(e)` that both stay
   well under the input's size, while `.line_text` still carries the full,
   untruncated line.
