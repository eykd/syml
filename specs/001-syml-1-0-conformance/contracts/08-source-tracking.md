# Contract 08 — Source tracking (§10): `as_source`, `Source`, `Pos`

**Requirements**: FR-012, FR-013, FR-017 | **User story**: US8
**Spec**: §10.1, §10.2, §10.3, §13.3 | **Audit gaps**: 16, 19 | **`todo.txt`**: B3
**Research**: R-02 (position mapping), R-07 (text equality)

## Surface

```python
# src/syml/basetypes.py

@dataclass(slots=True, frozen=True)
class Pos:
    index: int   # 0-indexed code-point offset into the ORIGINAL text
    line: int    # 1-indexed
    column: int  # 0-indexed code-point column


@dataclass(slots=True, repr=False, frozen=True)
class Source:
    filename: StrPath | None
    start: Pos
    end: Pos
    text: str

    def __eq__(self, other: object) -> bool: ...   # by text
    def __hash__(self) -> int: ...                 # by text
    def __add__(self, other: Source | str) -> Source: ...

    @classmethod
    def from_node(
        cls,
        pnode: PNode,
        line: Line,
        position_map: PositionMap,
        filename: StrPath | None = None,
    ) -> Source:
        """start/end = position_map.to_original(pos_at(line, pnode.start/end))
        (Contract 01). Never reads pnode.full_text, which is the LINE under
        per-line lexing (Contract 02)."""
```

`parse(document, filename).as_source()` returns the same shape as `as_data()`
with every leaf and every key a `Source` instead of a `str` (US8.1).

## What changes

| | 0.6.2 | 1.0.0 |
| --- | --- | --- |
| `Pos` coordinates | normalized text (and miscounted — gap #16) | **the caller's original text** (FR-013, **breaking**) |
| line counting | `str.splitlines()` | split on `\n` only (§13.3) |
| coverage | `as_source()` blanket-exempted by `# pragma: nocover` | fully tested, exemptions removed (FR-012) |
| `__hash__` | `# pragma: no cover` | tested |
| `Source.__add__` | dead `return self + other.text` after a `return` | deleted (`todo.txt` B3, FR-017) |
| `Source.from_node` | `(pnode, filename)`; positions via `Pos.from_str_index(pnode.full_text, …)` | `(pnode, line, position_map, filename)`; positions via `pos_at` + `to_original` |
| `Pos.from_str_index` | line/column by `utils.split_lines` (`splitlines`); also used by `nodes.fail_to_incorporate_node` on `pnode.full_text` | kept (with `Source.from_text`, which the existing tests use) but counts `\n` only (§13.3); **never** used for parse positions — on a per-line `full_text` it would report line 1 for every node. `OutOfContextNodeError` / `DuplicateKeyError` take their `position` from the node's stored `Source.start` |

## Original-text coordinates (FR-013, R-02)

`Source.from_node(pnode, line, position_map, filename)` builds each endpoint
as `position_map.to_original(pos_at(line, offset))` — `pos_at` (Contract 01)
lifts the line-local `pnode` offset to a normalized `Pos`, and `to_original`
maps it to the caller's text. The `line` and `position_map` reach it through
the visitor (Contract 02's entry point sets `visitor.line`), and the resulting
`Source` is stored on the node when it is created, so `as_source()` needs no
arguments.

| Original document | Value | `Pos` |
| --- | --- | --- |
| `"﻿key: value"` | `value` | index 6, line 1, column 6 — counting the mark (US8.2) |
| `"a: b\r\nc: d"` | `d` | index 9 — counting the carriage return (US8.3) |
| `"a: b\r\nc: d"` | `b` | start index 3, **end** index 4 (the `\r`, exclusive) — not 5 |
| `"a: b c\nx: y"` | key `x` | **line 2** — U+2028 does not terminate a line (US8.4, gap #16) |

The third row is why §13.3's `splitlines()` prohibition is a prerequisite rather
than an optimization: today it reports line 3, and no remapping layer can fix a
line count that was wrong before remapping.

## Line/column conventions (§10.2)

- lines 1-indexed, columns 0-indexed, character indices 0-indexed
- columns counted in **code points**, not bytes (§13.3)

## Equality and hashing (§10.3, R-07) — unchanged

`Source` compares and hashes **by its text**, so it is interchangeable with a
plain `str` as a dict key. §10.3 requires this, and then draws the consequence:

> Because Source objects compare and hash exactly as their text, an
> implementation MUST NOT rely on final mapping construction to detect duplicate
> keys (§8.3) ... Duplicate-key detection MUST occur during tree incorporation.

Contract 03 lands that detection (FR-007), which is what closes the collision
hazard. No change to `__eq__`/`__hash__` is needed or wanted — weakening them
would break the interchangeability §10.3 asks for.

## Quoted-value spans (red-team pass 5)

A quoted value's `text` is the **decoded** string (data-model §4), so its span
cannot also slice to `text`: for `k: "a\nb"` the raw token is six characters and
the decoded text three. Pinned:

- `start` is the **opening quote** — the same anchor Contract 05 uses for
  `MalformedQuotedStringError`, so an editor jumping to a value or to an error
  on it lands on the same column.
- `end` is just past the **closing quote** (exclusive), before any trailing
  ` *`.
- `text` is the decoded value, so `str(source) == node.as_data()` still holds.

## Continuation spans

When a `TextLeafNode` absorbs a continuation line:

- `start` stays at the value's first character — for a root scalar whose
  head line is indented, that is the first **preserved indent space**, not the
  `text` token, because `as_data()` keeps that indentation (§5.3; Contract 03
  § Root-scalar head indentation, red-team pass 13)
- `end` moves to the last accepted character
- `text` equals what `as_data()` returns for the same node, **including the
  indentation preserved past the baseline** (Contract 03, D11)

**Invariant**: `str(node.as_source()) == node.as_data()` for every node.

## Coverage (FR-012, constitution III)

The blanket `# pragma: nocover` over `nodes.py`'s `as_source` surface is
removed. `nodes.py` is at 100% today only because seventeen branches carry a
pragma, including the entire `as_source()` path, which is reachable and
demonstrably works (audit gap #19). After this feature the only permitted
pragmas in `src/` are provably-unreachable branches — `if TYPE_CHECKING:` blocks
qualify; a reachable-but-untested `as_source` does not (US8.5, SC-004).

## Hygiene (FR-017)

- `tests/test_nodes.py` is tracked and **0 bytes**. An untracked
  `tests/test_nodes.py.orig` (≈11 KB) exists, hidden by a global `*.orig`
  gitignore. The task **reads and folds it in**, or deletes it deliberately —
  it cannot be `git mv`'d into place, because git does not see it.
- The dead `return self + other.text` in `Source.__add__` is deleted.

## Test obligations

- Every table row above.
- `as_source()` over every shape: root scalar (indented head included), list,
  mapping, nested, multiline continuation, quoted value, key, and an absent
  value (`key:`, `-`: zero-width at the container's `source.end`).
- `Source("foo") == "foo"` and `{Source("foo"): 1}["foo"] == 1`.
- `Source.__hash__` exercised directly (no pragma).
- `rg 'pragma: no ?cover' src/syml/nodes.py` finds only `TYPE_CHECKING` blocks.
- A property test: for a generated document, every reported `Pos.index` slices
  the **original** text at the value's first character.
- The same property for spans: for every node of a single-line value,
  `original[start.index:end.index] == source.text` for an unquoted value
  (an indented root scalar included — its span starts at the indent), and
  `decode_single_quoted(slice) == source.text` or `decode_double_quoted(slice)
  == source.text` for a quoted one — dispatched on `slice[0]`, `'` or `"` —
  where `slice = original[start.index:end.index]` (Contract 04: both decoders
  take the full quote-to-quote match, which this slice is by construction),
  over a corpus that includes CRLF,
  bare-CR, and BOM documents **and quoted values on CRLF lines**. Excluding
  quoted values instead would leave `end` unchecked on exactly the lines where
  it lands one before a collapsed break. This is the test that catches an exclusive
  `end` mapped with `bisect_right` (Contract 01) — the start-only property above
  cannot, because a token's `start` never lands on a collapsed break unless the
  token is empty.
- `end` is **exclusive** (it is `pnode.end` today and stays so); a row with a
  CRLF-terminated value asserts `end.index` points at the `\r`.
