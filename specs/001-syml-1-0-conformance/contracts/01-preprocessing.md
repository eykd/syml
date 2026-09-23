# Contract 01 — Pre-processing (§9.0) and line splitting (§13.3)

**Requirements**: FR-002, FR-003, FR-013 | **User stories**: US2, US8
**Spec**: §9.0, §4.4, §4.8, §8.4, §13.3 | **Decisions**: D14, D5 | **Audit gaps**: 8, 13, 16
**`todo.txt`**: A3 (reversed on class), A7, A8, B1

> No fenced example below carries a literal trailing space; `␠` marks one.

## Surface

```python
# src/syml/preprocess.py  (new module)

@dataclass(slots=True, frozen=True)
class PositionMap:
    """Maps a position in normalized text back to the caller's original text."""

    bom_offset: int          # 0 or 1
    crlf_indices: tuple[int, ...]   # sorted normalized indices where \r\n collapsed

    def to_original(self, pos: Pos) -> Pos: ...


@dataclass(slots=True, frozen=True)
class Document:
    original: str
    normalized: str
    position_map: PositionMap
    filename: StrPath | None


def preprocess(text: str, filename: StrPath | None = None) -> Document:
    """Apply §9.0 steps 1-3. Raises TabIndentationError."""


def split_lines_lf(text: str) -> list[Line]:
    """Split on U+000A only. Never str.splitlines() (§13.3)."""


def is_blank(text: str) -> bool:
    """D14's blank predicate: the line is entirely U+0020/U+0009, in any
    mixture (including the empty line). The ONE definition, shared by step 3's
    tab scan and Contract 02's per-line loop."""


def pos_at(line: Line, offset: int) -> Pos:
    """A line-local offset as a NORMALIZED Pos:
    Pos(line.start + offset, line.number, offset). Callers pass the result
    through PositionMap.to_original before it reaches a Source or ParseError."""
```

`Line` is `(text: str, start: int, number: int)` — see `data-model.md` §2.

## Behaviour

### Step 1 — BOM (§9.0.1, §13.3)

| Input | Normalized | Note |
| --- | --- | --- |
| `"﻿key: value"` | `"key: value"` | exactly one stripped; `bom_offset = 1` |
| `"﻿﻿key: v"` | `"﻿key: v"` | second is ordinary content |
| `"key: ﻿"` | unchanged | not at index 0 |
| `"﻿"` | `""` | the empty document (§7.4) → `loads` returns `""` |
| `""` | `""` | |

### Step 2 — line endings (§9.0.2, §4.8)

| Input | Normalized | `crlf_indices` |
| --- | --- | --- |
| `"a: b\r\nc: d"` | `"a: b\nc: d"` | `(4,)` |
| `"a: b\rc: d"` | `"a: b\nc: d"` | `()` — one-for-one, no offset |
| `"a: b\r\r\nc"` | `"a: b\n\nc"` | `(5,)` — the bare CR converts, then the CRLF collapses |
| `"a: b\r"` | `"a: b\n"` | `()` |

Normalization runs on the raw text **before any grammar rule**, including inside
what will later be quoted-string content (§4.8).

**Implementation constraint — single pass.** Normalization MUST be one
left-to-right scan, e.g. `re.sub(r'\r\n|\r', ...)` with a position-tracking
replacement callback. Chained `str.replace('\r\n', '\n').replace('\r', '\n')`
produces the correct normalized *text* but cannot produce the offset table: on
`"a: b\r\r\nc"` the first pass rewrites the `\r\n`, and the second then sees a
`\r` that the original document never had adjacent to a `\n`, so the recorded
collapse positions no longer describe the original. The `\r\r\n` row above is
the case that discriminates the two implementations, and it is one of the
red-team targets named in research.md.

### Step 3 — blank classification, then the tab scan (§9.0.3, D14)

Per line, compute the **leading-whitespace run**: the maximal run of U+0020 and
U+0009, in any mixture, from the start of the line.

1. If nothing follows that run before the next line boundary or end of document,
   the line is **blank** (§4.4, `is_blank`) — **skip the tab check entirely**,
   even if the run contains a tab. A blank line is also **never lexed**: D14
   says it is "discarded before any other check", and Contract 02's per-line
   loop drops it with the same `is_blank` before calling the grammar.
   `preprocess` itself cannot remove the line — `normalized` keeps every break
   so `line` numbers and `PositionMap` stay one-for-one with the original.
2. Otherwise, if the run contains a tab anywhere, raise `TabIndentationError`,
   positioned at the **first** tab in the run. The scan runs on the normalized text (after steps
   1–2), so the position is passed through `to_original` like every other:
   `"\ufeff\tkey: v"` reports the tab at column **1**, index 1 (the BOM
   counts), with `line_text` the original line including the BOM (Contract 05).

| Input | Result |
| --- | --- |
| `"\tkey: value"` | `TabIndentationError` |
| `"key: a\n\tb"` | `TabIndentationError` — a continuation line gets no exemption |
| `"  \t  \nkey: v"` | no error — line 1 is blank (US2 scenario 6); `loads` → `{"key": "v"}` |
| `"\t"` | no error — blank; `loads` → `""` |
| `"key: a\n  \t\n  b"` | no error; `loads` → `{"key": "a\nb"}` — a tab-bearing blank line inside a value is discarded (D12), not appended as `"\t"` |

The three `loads` results are asserted through `loads`, not only through
`preprocess`: under `indent = ~" *"` the line `"  \t  "` lexes as `indent`
`"  "` plus `data` `"\t  "` (verified 2026-09-23), a **non-empty** scalar at
level 2. If the loop does not drop it, `"  \t  \nkey: v"` makes it the root
scalar and then raises `OutOfContextNodeError` on `key: v` — while a unit test
of `preprocess` alone still passes.
| `"key:\tv"` | no error — the tab is not in *leading* whitespace (D5) |
| `"key: \tv"` | no error — same (D5) |
| `"\ufeff\tkey: v"` | `TabIndentationError` at `Pos(1, 1, 1)` — original coordinates |

The scan applies uniformly to every physical line. There is no special case for
"the tab is really the first character of the continuation's content" (§9.0).

### Line splitting (§13.3, FR-003)

Only U+000A terminates a line. U+2028, U+2029, U+0085, U+000B, U+000C,
U+001C–U+001E do **not** — for tokenization, position tracking, or error line
numbering.

| Input | Lines | Note |
| --- | --- | --- |
| `"a: b c\nx: y"` | `["a: b c", "x: y"]` | US2 scenario 7, US8 scenario 4 |

`src/syml/utils.py`'s `split_lines`/`get_line` currently call
`str.splitlines()`; §13.3 forbids it by name. Both are replaced. This is a
prerequisite for Contract 08 — audit gap #16 (`x` reported on line 3 instead of
line 2) is caused by it, and no amount of position remapping fixes it.

## PositionMap

```python
to_original(Pos(index=i, line=l, column=c)) -> Pos(
    index  = i + bom_offset + bisect_left(crlf_indices, i),
    line   = l,
    column = c + bom_offset if l == 1 else c,
)
```

| Original | Normalized `Pos` | Original `Pos` |
| --- | --- | --- |
| `"﻿key: value"`, value `value` | `(5, 1, 5)` | `(6, 1, 6)` |
| `"a: b\r\nc: d"`, key `c` | `(5, 2, 0)` | `(6, 2, 0)` |
| `"a: b\r\nc: d"`, value `b`'s exclusive **end** | `(4, 1, 4)` | `(4, 1, 4)` — the `\r`, so `original[3:4] == "b"` |
| `"k:␠\r\nx: y"`, the empty value of `k:␠` (start = end) | `(3, 1, 3)` | `(3, 1, 3)` — the `\r` |

**Invariants**

- `to_original` is monotonically non-decreasing in `index`.
- `line` is never remapped: §9.0 substitutes one break for one break.
- `bisect_left` (not `bisect_right`): a position **at** a collapsed break maps
  to the `\r`, the first character of the original break. The only positions
  that ever land on a collapsed-break index are the exclusive `end` of a token
  that ends a CRLF-terminated line, and the `start`/`end` of an empty token at
  end of line (`key:`, `-`). Both mean "the end of this line's content", which
  in the original text is the `\r`. `bisect_right` would put them on the `\n`,
  giving a `Pos` whose `index` disagrees with its own `line`/`column` and making
  `original[start.index:end.index]` include the `\r` — i.e. **every** value on
  a CRLF line would report an `end` one past its last character.
  (Red team 2026-09-23: brute-forced 97,855 positions over random BOM/CR/CRLF
  documents; `bisect_left` is consistent at all of them, `bisect_right` is
  inconsistent at 18,654 — exactly the positions in `crlf_indices`.)
- **Consistency**: for every normalized position, the mapped `index` is the
  original offset of the mapped `(line, column)`, counting `\r\n`, bare `\r`,
  and `\n` each as one break and a leading BOM as a column-0 character.

## Errors raised

`TabIndentationError` only. Contract 05 gives its attribute shape.

## Test obligations

- Every row of every table above, as a unit test.
- `rg 'splitlines' src/` finds nothing.
- `to_original` round-trips against a brute-force reference implementation over
  a generated corpus mixing BOM, CRLF, bare CR, and ` `.
- The two `\r\r\n` and trailing-bare-`\r` rows are the red-team targets named in
  research.md's open items.
