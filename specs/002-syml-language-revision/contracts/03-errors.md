# Contract 03 — Error Text, Hints, Filenames, and Positions

**Requirements**: FR-011, FR-012, FR-013, FR-016 (§8.3 example) | **Decisions**: D7 affirmed (one class for §8.1/§8.2) | **Findings closed**: `syml-xreq.4`, `.5`, `.9` (§8.3 half), `.17` (hint half), `.18`, `.3` (hint half) | **Research**: R-07, R-08, R-09

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

Private state: `_description: str`, `_filename: StrPath | None` (`""`
normalizes to `None`). No new public attribute. `.args` is
`(self.message, position, line_text, *extra)`.

`__str__`:

```text
<filename>:<line>:<column>: <description>
<line_text>
```

The `<filename>:` part is omitted when there is none. `<line>` is 1-indexed,
`<column>` 0-indexed (§10.2), both from `self.position`.

## Messages

| Class | Description (the part after any filename prefix) |
| --- | --- |
| `OutOfContextNodeError` | When `C` is not an open column: `Line {L}, at column {C}, does not fit any open block; open blocks are at {COLS}.` When `C` is an open column whose block holds the other kind of entry (§6.4): `Line {L}, at column {C}, is a {KIND}, but the open block at column {C} holds {OTHER}; open blocks are at {COLS}.` (`KIND`/`OTHER` from `list item`/`keys`, `key`/`list items`, `text line`/`keys` or `list items`). Either form is optionally followed by one space and a hint |
| `DuplicateKeyError` | `Duplicate key '{key}'` (unchanged attributes `key`, `first_position`) |
| `TabIndentationError` | `A tab character was found in a line's leading whitespace` (unchanged) |
| `EncodingError` | `Invalid encoding` (unchanged) |

`{COLS}` is `column 0` for one column, `columns 0 and 2` for two,
`columns 0, 2 and 4` for more: the sorted distinct levels of the `List` and
`Mapping` nodes on `Root`'s rightmost spine at the time of failure (R-08). The
list is never empty: `Root` can only fail once its first child is a `List` or
`Mapping` (a root scalar absorbs every later line).

Hints (at most one; (b) is checked first):

- **(b) list at its key's column**: the failing node is a `ListItem` and the
  spine ends in a childless `KeyValue` at the same level →
  `Hint: a list under a key must be indented past the key's column.`
- **(a) would-be key**: the failing line, or the previous non-blank line,
  after its indentation spaces, is `RUN:` followed by a space, a tab, or end of
  line, where `RUN` is a non-empty run of characters that are neither
  whitespace nor `:` and does not fully match `[a-z][a-z0-9_-]*` →
  `Hint: 'RUN' is not a key; a key is lowercase ASCII letters, digits, '-' and '_', starting with a letter.`

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
   filename, and with `filename=""`.
3. `pickle.loads(pickle.dumps(e))` preserves `str(e)`, `.message`, `.args`,
   and (for `DuplicateKeyError`) `.key` / `.first_position`.
4. The column list formatter: one, two, and three columns; both message forms
   (column not open; open column of the other kind, incl. `- item\nkey: value`
   and `a:\n  b: 1\n  plain`).
5. Hint (a) fires on the failing line and on the line above; does not fire for
   `a: 1\nb` or for a line whose colon is followed by a non-space; hint (b)
   fires for `k:\n- a` and `- key:\n  - x`, not for `k:\n  - a\n- b`.
6. SC-007's three cases as acceptance scenarios (US11).
