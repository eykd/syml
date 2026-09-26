# Contract 03 — Error Text, Hints, Filenames, and Positions

> Amended 2026-09-25 by D26, D27, D30, D31, D32, D33, D34, D35 (break-test round 2, `syml-cjk2`); rows that change are updated by the leaf that implements them.

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

The `<filename>` segment gets a related but distinct treatment (`syml-cjk2.5`
break-testing round 2, refined by D34/`syml-cjk2.19`): `filename` is
caller-controlled and normally short, but its length is not otherwise
bounded (e.g. an archive entry path or a hostile CLI argument), so both
`error_message(description, filename)` (which builds `.message`'s prefix)
and `__str__`'s `<filename>:` segment window it through a dedicated private
helper, `_truncated_filename_window(filename, width=1024)`, before
quoting/escaping it. Unlike `_truncated_window`'s centered window,
`_truncated_filename_window` always elides from the **head**: a filename up
to 1024 code points passes through whole; a longer one is rendered as
`'…'` plus its last `width - 1` code points. A path's basename — the part a
`path:line:col` reader needs to find the file — sits at the tail, so
eliding the head instead of centering the window keeps it intact regardless
of how long the filename's leading directories are; `syml-cjk2.5`'s original
80-code-point head-centered window cut the basename off any real-world
absolute path longer than 80 characters (routine for CI runner paths),
silently breaking the clickable `path:line:col` form. A 2 MB `filename`
still yields a bounded `.message` and `str(e)` instead of scaling with the
filename's length, and its basename still appears in full.

`DuplicateKeyError`'s description gets the same treatment (`syml-s9p9.14`):
the grammar's key pattern (`[a-z][a-z0-9_-]*`) has no length bound, so a
document that repeats a 1 MB key used to yield a multi-megabyte `.message`
and `str(e)`. `duplicate_key_description(key, first_line)` windows `key`
through `_truncated_window(key, center=0)` before quoting it — the same call
shape as hint (a)'s would-be-key quote — so `.message` stays bounded
regardless of the repeated key's length; `first_line` (an `int`, unbounded
by nature) is appended unwindowed as `(first defined at line {first_line})`
(D32, syml-cjk2.16). `DuplicateKeyError.key` and `.args` still carry the
full, untruncated key.

## Messages

| Class | Description (the part after any filename prefix) |
| --- | --- |
| `OutOfContextNodeError` | When `C` is not an open column: `Line {L}, at column {C}, does not fit any open block; open blocks are at {COLS}.` When `C` is an open column whose block holds the other kind of entry (§6.4): `Line {L}, at column {C}, is a {KIND}, but the open block at column {C} holds {OTHER}; open blocks are at {COLS}.` (`KIND`/`OTHER` from `list item`/`keys`, `key`/`list items`, `text line`/`keys` or `list items`). Either form is optionally followed by the text-value clause (below), then by one space and a hint |
| `DuplicateKeyError` | `Duplicate key '{key}' (first defined at line {N})`, `key` windowed through `_truncated_window(key, center=0)`, `N` = `first_position.line` (D32) (unchanged attributes `key`, `first_position`, both carrying the full key) |
| `TabIndentationError` | `A tab character was found in a line's leading whitespace` (unchanged) |
| `EncodingError` | `Invalid UTF-8 (byte 0x{XX}); save the file as UTF-8` when the failing codec normalizes to UTF-8 (`codecs.lookup(err.encoding).name == 'utf-8'`, including bytes input); otherwise `Invalid {codec} (byte 0x{XX})`, naming the caller-supplied stream's actual codec and dropping the UTF-8-specific advice. `{XX}` the first offending byte in lowercase two-digit hex (D31, refined by `syml-cjk2.21`) |
| `UnrepresentableValueError` / `dumps`'s `TypeError` | Not a `ParseError` (defined and raised by the serializer, Contract 04 §Unrepresentable set); documented here because D30 gives both the same `str(e)` shape as the classes above. `str(e)` is the message alone — never a tuple repr of `.args` — with the offending value's data path appended as a Python subscript clause (`at ['a']['b'][1]`) when it is not the root value; a root value's message has no path clause. `UnrepresentableValueError` gains a public `.path` attribute, `tuple[str \| int, ...]`, `()` at the root; a bad mapping key is pathed to its parent mapping. The rendered path clause is bounded the same way a hostile `DuplicateKeyError` key is (`_truncated_window` per segment, depth capped to the first and last three segments with one `'…'` between); `.path` itself, and the tuple a caller passed in, are never truncated. The `dumps` `TypeError` stays a plain builtin `TypeError`, message only — no `.path` attribute, no new subclass (D30, `syml-cjk2.14`; full detail in Contract 04 §Error text and the data path) |

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

Hints (at most one; checked in the order (b), (d), (e), (a), (c) — (d)/(e)
sit ahead of (a)/(c) so a comment or document-marker line never gets a
misleading "not a key"/"needs a space" hint about its own shape, §"(d)"
below):

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
- **(c) missing space after a marker** (D26, `syml-cjk2.10`; amended by D35,
  `syml-cjk2.20`): the failing
  line, or the line above under (a)'s exact look-back (same candidate line,
  same gate on it being the value's first line and the failing node being a
  `KeyValue`/`ListItem`), after its indentation spaces, matches
  `[a-z][a-z0-9_-]*:(?!//)\S` (a key immediately followed by a non-space
  character, but not `://` — a URL value such as `http://example.com` or
  §8's `url: https://example.com:8080/path` never counts, D35) or `-(?!-)\S`
  (a list marker immediately followed by a
  non-space character, `--`/`---`/`...` excluded — those are hint (e)'s
  document-marker territory, not this one's) →
  `Hint: a key or list marker needs a space after it.` **Failing-line
  gating** differs from (a): (c) fires on either open-column kind (`{COLS}`
  holding `keys` *or* `list items`, i.e. form 2 of the message), never on
  form 1 (`C` not an open column) — there the real problem is indentation,
  not a missing space, and the hint would mislead (`config:\n  Host: x\n
  port:8080`, column 1 not open, gets no hint). (a) and (c) never both match
  the same candidate line: (a)'s pattern requires whitespace or end-of-line
  after the colon, (c)'s requires a non-space character there.
- **(d) indented comment** (D27, `syml-cjk2.11`): the **failing line only**
  (no look-back), after its indentation spaces, starts with `#` or `//` →
  `Hint: comments must start at column 0; an indented '#' line is text.`
  Not gated on `{COLS}`: the problem is a property of the line's content,
  not its indentation, so it fires on form 1 and form 2 alike. Checked
  *before* (a)/(c) on the failing line (that ordering is why the overall
  hint order is (b), (d), (e), (a), (c)): `#port: 80` (no space after `#`)
  would otherwise also match (a)'s `RUN:` pattern (`RUN` = `#port`) and
  wrongly suggest renaming a key, when the real problem is the leading `#`.
- **(e) mid-file document marker** (D27, `syml-cjk2.11`): the **failing
  line only** (no look-back), after its indentation spaces and before any
  trailing spaces/tabs, is exactly `---` or `...` →
  `Hint: SYML has no document markers.` Also not gated on `{COLS}`, for the
  same reason as (d). `--x`/`--` never match (only an exact `---` or `...`
  line does); those get no hint at all, same as before D27.

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
| FR-013 | `a: 1\na: 2`, `""` | `.message == "Duplicate key 'a' (first defined at line 1)"` (no `": "` prefix) (D32) |
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
| hint (c), `syml-cjk2.10` | `server:\n  host: x\n  port:8080` | `OutOfContextNodeError`; description `Line 3, at column 2, is a text line, but the open block at column 2 holds keys; open blocks are at columns 0 and 2. Hint: a key or list marker needs a space after it.` |
| hint (c), `syml-cjk2.10` | `l:\n  - a\n  -b` | description `Line 3, at column 2, is a text line, but the open block at column 2 holds list items; open blocks are at columns 0 and 2. Hint: a key or list marker needs a space after it.` |
| hint (c), `syml-cjk2.10` | `k:\n  port:8080\n- x` | hint (c) fires from the line above (D26's look-back), naming no run — description ends `Hint: a key or list marker needs a space after it.` |
| hint (c) gate, `syml-cjk2.10` | `server:\n  host: x\n port:8080` | no hint (column 1 is not an open block — form 1 — even though the line is missing its space; the real problem is indentation) |
| hint (c) gate, `syml-cjk2.10` | `needs_space_after_marker('---')` / `'--x'` | both `False` — a document-marker-shaped line never gets hint (c); hint (e) owns that |
| hint (d), `syml-cjk2.11` | `server:\n  host: a\n  # port: 80\n  port: 81` | `OutOfContextNodeError`; description `Line 3, at column 2, is a text line, but the open block at column 2 holds keys; open blocks are at columns 0 and 2. Hint: comments must start at column 0; an indented '#' line is text.` |
| hint (d), `syml-cjk2.11` | `server:\n  host: a\n // c\n  port: 81` | hint (d) fires for `//` too |
| hint (d) form 1, `syml-cjk2.11` | `server:\n  host: a\n # comment\n  port: 81` | hint (d) fires even though column 1 is not an open block (form 1) — unlike (c), (d) is not gated on `{COLS}` |
| hint (d) precedence, `syml-cjk2.11` | `server:\n  host: a\n  #port: 80\n  port: 81` | hint (d) wins over (a): message contains "comments must start at column 0", not "is not a key" |
| hint (e), `syml-cjk2.11` | `k: v\n---\nj: w` | `OutOfContextNodeError`; description `Line 2, at column 0, is a text line, but the open block at column 0 holds keys; open blocks are at column 0. Hint: SYML has no document markers.` |
| hint (e), `syml-cjk2.11` | `k:\n  v\n...\n` | description ends `; the open value continues at column 2. Hint: SYML has no document markers.` |
| hint (e) gate, `syml-cjk2.11` | `server:\n  host: a\n  --x\n  port: 81` | no hint (`--x` is not `---` or `...` exactly) |
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
- `Mapping.can_add_node` raises `DuplicateKeyError(duplicate_key_description(key, first.source.start.line), ..., filename=node.filename)`;
  `duplicate_key_description` windows `key` through `_truncated_window(key, center=0)`
  before quoting it, the same treatment hint (a) gives a would-be key (§Bounded rendering, syml-s9p9.14),
  then appends `(first defined at line {first_line})` unwindowed (D32, syml-cjk2.16).
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
6a. Hint (c) (D26, `syml-cjk2.10`): fires on the failing line for both
   open-column kinds (`server:\n  host: x\n  port:8080`; `l:\n  - a\n  -b`)
   and on the line above via (a)'s exact look-back
   (`k:\n  port:8080\n- x`); does not fire on form 1
   (`server:\n  host: x\n port:8080`, the indentation-error case); never
   fires alongside hint (a) on the same candidate line (they are mutually
   exclusive by construction). `needs_space_after_marker`'s own truth table:
   `key:value` / `-x` (indented or not) → `True`; `key: value` / `key:` /
   `- x` / `a plain line` → `False`; `---` / `--x` / `...` → `False` (never
   a document-marker-shaped line — `.11`'s territory).
7. SC-007's three cases as acceptance scenarios (US11).
8. `_printable`: `str(e)` contains no character outside `str.isprintable()`
   except the one `\n` between its two lines, for every raised error in the
   SC-002/P3 property run (the property asserts it on each `ParseError`).
9. Bounded rendering (`syml-s9p9.9`): a hostile 1 MB line (e.g. a run of
   `\x00` before a bare `:`) yields a `.message` and `str(e)` that both stay
   well under the input's size, while `.line_text` still carries the full,
   untruncated line. Bounded rendering also covers `DuplicateKeyError`
   (`syml-s9p9.14`): a document repeating a 1 MB key yields a `.message` and
   `str(e)` well under the input's size, while `.key` still carries the
   full, untruncated key. Bounded rendering also covers a hostile `filename`
   (`syml-cjk2.5`, `syml-cjk2.19`/D34): a caller- or attacker-supplied
   filename of a million-plus characters yields a `.message` and `str(e)`
   that both stay well under the filename's size, for both a raise reached
   through the builder (e.g. `OutOfContextNodeError`) and through
   `EncodingError`, and — since the window elides the filename's head, not
   its tail — the filename's own basename still appears in full at the end
   of the windowed segment. An ordinary absolute path up to 1024 code
   points (routine for CI runner paths, e.g. an 85-character path) is
   rendered whole, unelided.
