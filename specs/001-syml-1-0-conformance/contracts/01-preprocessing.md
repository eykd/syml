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
   the line is **blank** (§4.4) — **skip the tab check entirely**, even if the
   run contains a tab.
2. Otherwise, if the run contains a tab anywhere, raise `TabIndentationError`,
   positioned at the **first** tab in the run.

| Input | Result |
| --- | --- |
| `"\tkey: value"` | `TabIndentationError` |
| `"key: a\n\tb"` | `TabIndentationError` — a continuation line gets no exemption |
| `"  \t  \nkey: v"` | no error — line 1 is blank (US2 scenario 6) |
| `"\t"` | no error — blank |
| `"key:\tv"` | no error — the tab is not in *leading* whitespace (D5) |
| `"key: \tv"` | no error — same (D5) |

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
    index  = i + bom_offset + bisect_right(crlf_indices, i),
    line   = l,
    column = c + bom_offset if l == 1 else c,
)
```

| Original | Normalized `Pos` | Original `Pos` |
| --- | --- | --- |
| `"﻿key: value"`, value `value` | `(5, 1, 5)` | `(6, 1, 6)` |
| `"a: b\r\nc: d"`, key `c` | `(5, 2, 0)` | `(6, 2, 0)` |

**Invariants**

- `to_original` is monotonically non-decreasing in `index`.
- `line` is never remapped: §9.0 substitutes one break for one break.
- `bisect_right` (not `bisect_left`): a position at a collapsed break maps to
  the `\n`, not the `\r`.

## Errors raised

`TabIndentationError` only. Contract 05 gives its attribute shape.

## Test obligations

- Every row of every table above, as a unit test.
- `rg 'splitlines' src/` finds nothing.
- `to_original` round-trips against a brute-force reference implementation over
  a generated corpus mixing BOM, CRLF, bare CR, and ` `.
- The two `\r\r\n` and trailing-bare-`\r` rows are the red-team targets named in
  research.md's open items.
