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

    def __eq__(self, other: object) -> bool:       # by text; str and Source only
        if isinstance(other, Source):
            return self.text == other.text
        if isinstance(other, str):
            return self.text == other
        return NotImplemented                       # pass 20: never str(other)

    def __hash__(self) -> int:                     # by text
        return hash(self.text)

    def __add__(self, other: Source | str) -> Source: ...   # kept; no parse path uses it

    @classmethod
    def from_node(
        cls,
        pnode: PNode,
        line: Line,
        position_map: PositionMap,
        filename: StrPath | None = None,
    ) -> Source:
        """start/end = position_map.to_original(pos_at(line, pnode.start/end))
        (Contract 01; pos_at is defined in this module). text = pnode.text.
        Never reads pnode.full_text, which is the LINE under per-line lexing
        (Contract 02). position_map is a TYPE_CHECKING-only import: this
        module must not import preprocess at run time (Contract 01)."""
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
| `Source.__add__` | dead `return self + other.text` after a `return`; the `str` branch's `end.index` omits the joining `\n`, `Source + ''` raises `IndexError`, and line counting goes through `splitlines()` | dead `return` deleted (`todo.txt` B3, FR-017). The `str` branch counts the joining `\n` and splits on `\n` only (below). **No parse path calls `__add__`**: `TextLeafNode.as_source()` builds its `Source` directly (Contract 03) |
| `Source.__eq__` | `str(self) == str(other)`: `Source('1') == 1` and `Source('None') == None` are `True`, with unequal hashes | `str` and `Source` only; anything else is `NotImplemented`, so `Source('1') == 1` is `False` (pass 20) |
| `Source.from_node` | `(pnode, filename)`; positions via `Pos.from_str_index(pnode.full_text, …)` | `(pnode, line, position_map, filename)`; positions via `pos_at` + `to_original` |
| `Pos.from_str_index` | line/column by `utils.split_lines` (`splitlines`); also used by `nodes.fail_to_incorporate_node` on `pnode.full_text` | kept (with `Source.from_text`, which the existing tests use) but counts `\n` only (§13.3) by counting in `text[:index]` itself, not through `utils` (deleted, Contract 01, pass 25); an index past the end clamps to `len(text)`; **never** used for parse positions — on a per-line `full_text` it would report line 1 for every node. `OutOfContextNodeError` / `DuplicateKeyError` take their `position` from the node's stored `Source.start` |

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
| `"\ufeffkey: value"` | `value` | index 6, line 1, column 6 — counting the mark (US8.2) |
| `"a: b\r\nc: d"` | `d` | index 9 — counting the carriage return (US8.3) |
| `"a: b\r\nc: d"` | `b` | start index 3, **end** index 4 (the `\r`, exclusive) — not 5 |
| `"a: b\u2028c\nx: y"` | key `x` | **line 2** — U+2028 does not terminate a line (US8.4, gap #16) |

The third row is why §13.3's `splitlines()` prohibition is a prerequisite rather
than an optimization: today it reports line 3, and no remapping layer can fix a
line count that was wrong before remapping.

## Line/column conventions (§10.2)

- lines 1-indexed, columns 0-indexed, character indices 0-indexed
- columns counted in **code points**, not bytes (§13.3)

## Equality and hashing (§10.3, R-07) — text equality kept, non-`str` operands removed

`Source` compares and hashes **by its text**, so it is interchangeable with a
plain `str` as a dict key. §10.3 requires this, and then draws the consequence:

> Because Source objects compare and hash exactly as their text, an
> implementation MUST NOT rely on final mapping construction to detect duplicate
> keys (§8.3) ... Duplicate-key detection MUST occur during tree incorporation.

Contract 03 lands that detection (FR-007), which is what closes the collision
hazard. Text equality and text hashing stay exactly as they are — weakening
them would break the interchangeability §10.3 asks for. Only the non-`str`
operands below change.

**`__eq__` compares with `str`s and `Source`s only (red-team pass 20).**
Today's `__eq__` is `str(self) == str(other)`, which is broader than "exactly
as their text": a `str` `'1'` does not equal the `int` `1`, but `Source('1')`
did, and `Source('None') == None` was `True`. It also broke Python's rule
that equal objects hash equal (`hash(Source('1')) != hash(1)`, so
`Source('1') in {1}` was `False` while `Source('1') == 1` was `True`;
verified). Returning `NotImplemented` for any other type keeps every
`str`-interchangeability §10.3 and R-07 require, `{src: 1}['foo']` and
`'foo' == src` included, and removes only the accidental cases. No D1-D17
decision is touched. `dataclasses.replace(source, text=...)` (the quoted-value
path below) builds a new frozen `Source` that compares and hashes by the new
text, and `Source` survives `pickle` and `copy.deepcopy` (verified).

**Consequence for tests: `==` never checks a position.** Because equality
is by text alone, `as_source() == {Source(...): Source(...)}` and
`new_source == Source(start=..., end=...)` pass whatever the positions are.
Today's `tests/test_basetypes.py` and `tests/test_parsers.py` assert
positions exactly that way, which is how the `__add__` index error above
survived. Every position obligation in this contract compares `.start` and
`.end` (or `(s.start, s.end, s.text)` tuples), never whole `Source`s.

**`Source.__add__`'s `str` branch (pass 20).** Kept for API compatibility,
so it is covered by direct tests, but its positions are synthetic: no parse
path calls it, and the result is not a span of any document. The corrected
arithmetic, for `self + other`:

```python
lines = other.split('\n')                        # LF only (§13.3), never splitlines
end = Pos(index=self.end.index + 1 + len(other),  # +1: the joining '\n'
          line=self.end.line + len(lines),
          column=len(lines[-1]))
text = f'{self.text}\n{other}'                    # '' is valid: one empty line
```

The whole method, so the other two arms are not lost in transcription
(pass 25: an assembly that transcribed only the `str` arm turned `Source + 5`
into an `AttributeError`):

```python
def __add__(self, other: Source | str) -> Source:
    if isinstance(other, str):
        ...                                   # the str arm above
        return Source(filename=self.filename, start=self.start, end=end, text=text)
    if isinstance(other, Source):
        return Source(filename=self.filename, start=self.start, end=other.end,
                      text=f'{self.text}\n{other}')
    raise TypeError('Tried to add invalid type to Source', type(other))  # kept from 0.6.2
```

`Pos.from_str_index`, LF-only with 0.6.2's past-end clamp (pass 25):

```python
index = min(index, len(text))
before = text[:index]
return cls(index, before.count('\n') + 1, index - (before.rfind('\n') + 1))
```

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
  `from_node` yields the raw token text, so `visit_quoted_value` replaces it
  with `dataclasses.replace(source, text=decoded)` (`Source` is frozen), in
  the same method that decodes and converts decoder defects (Contract 05,
  red-team pass 17).

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
pragmas in `src/` are `if TYPE_CHECKING:` blocks (plan.md Principle III row);
a reachable-but-untested `as_source` does not qualify (US8.5, SC-004), and
the base-class stubs no input reaches are deleted or covered by direct
tests (Contract 03 § Coverage without pragmas, pass 23).

`basetypes.py`'s `Source.from_text`'s `if substring is None: # pragma: no
cover` also goes (pass 23): a direct call with no `substring` (the default)
covers the branch, so no fill-in is needed to reach it — only a caller that
always passes `substring` left it unreached.

## Hygiene (FR-017)

- `tests/test_nodes.py` is tracked and **0 bytes**. An untracked
  `tests/test_nodes.py.orig` (≈11 KB) exists, hidden by a global `*.orig`
  gitignore. The task **reads and folds it in**, or deletes it deliberately —
  it cannot be `git mv`'d into place, because git does not see it.
- The dead `return self + other.text` in `Source.__add__` is deleted, and its
  `str` branch's arithmetic is corrected (§ Equality and hashing, pass 20).

## Test obligations

- Every table row above.
- `as_source()` over every shape: root scalar (indented head included), list,
  mapping, nested, multiline continuation, quoted value, key, and an absent
  value (`key:`, `-`: zero-width at the container's `source.end`).
- With `src = Source(filename=None, start=Pos(0, 1, 0), end=Pos(3, 1, 3),
  text='foo')` (all four fields are required): `src == "foo"` and
  `{src: 1}["foo"] == 1`.
- `Source.__hash__` exercised directly (no pragma).
- (`Source('x')` below is shorthand for a `Source` with text `'x'` and any
  positions; all four fields are required.) `Source('1') == 1`,
  `Source('None') == None`, and `Source('a') == ['a']` are all `False`; `Source('foo') == 'foo'`, `'foo' == Source('foo')`, and
  `Source('foo') == Source('foo', other positions)` are `True` (pass 20).
- `Source.__add__`: `src + 'x'` has `end.index == src.end.index + 2`;
  `src + ''` returns a `Source` whose text ends in `\n`; both assert `.end`
  field by field. `Source + Source` takes the right operand's `end`.
- No position assertion anywhere compares whole `Source` objects with `==`
  (see § Equality and hashing).
- `rg 'pragma: no ?(cover|branch)' src/` finds only `TYPE_CHECKING` blocks
  (pass 23 widened this from `nodes.py` alone; Contract 03 § Coverage
  without pragmas lists what replaces each of today's pragmas).
- `Source.from_text(text)` called with no `substring` (no pragma).
- The rest of `basetypes.py` that no parse path reaches, each asserted
  directly (pass 25: an assembly of Contracts 01-08 run under this repo's
  branch coverage over **only** the obligations listed in Contracts 01-08
  left exactly these uncovered, plus Contract 06's explicit-`filename`
  branch). Today's `tests/test_basetypes.py` covers the first three, but by
  whole-`Source` `==`, so each is rewritten to compare fields, not dropped:
  - `Source.from_text(text, substring)` with a `substring`, asserting
    `.start`/`.end` field by field (the `substring is None` false arm);
  - `Source.from_text('foo', 'bar')` raises `ValueError` (no match);
  - `repr()` of a `Source` with and without a `filename`;
  - `Source + 5` raises `TypeError`. Today's explicit `raise TypeError`
    after the `str` and `Source` branches stays; only the dead `return`
    above it goes (FR-017).
- `{src: 1}["foo"] == 1` is a mypy `index` error in the type-checked test
  module (`dict[Source, int]` indexed by `str`; verified, pass 25), so it
  carries `# type: ignore[index]`, as today's test does. §10.3's
  interchangeability holds at run time and is not expressible to mypy.
- `Pos.from_str_index(text, i)` with `i > len(text)` clamps to `len(text)`
  and counts it the same way (pass 25). Today's
  `test_returns_last_line_and_first_column_of_bad_index` text ends in `\n`,
  so LF-only counting puts its end at line 7, column 0, where 0.6.2's
  `splitlines(keepends=True)` walk said line 6. The test's expected line
  changes to 7 with the counting; it is not a regression.
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
