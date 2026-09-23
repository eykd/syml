# Contract 06 — `loads`, `load`, `parse` (§11.1, §11.2)

**Requirements**: FR-005, FR-009, FR-010 | **User stories**: US4, US5
**Spec**: §7.3, §7.4, §11.1, §11.2, §13.3 | **Audit gap**: 18 | **Research**: R-04

## Surface

```python
# src/syml/__init__.py

SymlData = str | list["SymlData"] | dict[str, "SymlData"]

def loads(document: str, filename: StrPath | None = None) -> SymlData: ...

def load(
    file_obj: IO[str] | IO[bytes],
    filename: StrPath | None = None,
) -> SymlData: ...

def parse(document: str, filename: StrPath | None = None) -> Root: ...
```

### Changes from 0.6.2

| | 0.6.2 | 1.0.0 |
| --- | --- | --- |
| `load` parameter type | `TextIOBase` | `IO[str] \| IO[bytes]` (**breaking, widening**) |
| return type | `list \| dict \| str` (with `None` leaves) | `SymlData` — never `None` at any depth |
| exceptions | Parsimonious may escape | only `ParseError` subclasses |

`parse` is promoted from an internal in `syml.parsers` to a documented §11.2
export; it is the entry point for source tracking (Contract 08).

## `loads`

Applies Contract 01's pre-processing, Contract 02's per-line lexing, Contract
03's tree building, then `Root.as_data()`.

| Document | Result | Requirement |
| --- | --- | --- |
| `""` | `""` | FR-005, §7.4 (US4.2) |
| `"# just a comment"` | `""` | FR-005, §7.4 (US4.3) |
| `"﻿"` | `""` | FR-002 (US2.2) |
| `"empty:\nnext: value"` | `{"empty": "", "next": "value"}` | FR-005 (US4.1) |
| `"hello"` | `"hello"` | §2.1 |
| `"- a\n- b"` | `["a", "b"]` | §2.1 |

**Invariant (FR-005)**: walking any result to its leaves finds only `str`,
`list`, and `dict`. No `None` at any depth (US4.5).

**Invariant (FR-009)**: any exception raised is a `ParseError` subclass, for
every input in the audit's corpus and the acceptance suite — other than
documents beyond the documented nesting limitation (SC-005, spec Edge Cases).

## `load`

```python
def load(file_obj, filename=None):
    raw = file_obj.read()
    if isinstance(raw, bytes):
        try:
            text = raw.decode('utf-8')          # strict: no errors= substitution
        except UnicodeDecodeError as err:
            raise EncodingError(...) from err   # R-04's position derivation
    else:
        text = raw
    if filename is None:
        filename = getattr(file_obj, 'name', None)
    return loads(text, filename=filename)
```

Dispatch is on the **value** returned by `read()`, not on the handle's declared
type — duck typing is the norm for file-likes, and `io.BytesIO` / `io.StringIO`
both satisfy the protocol without inheriting from `TextIOBase`.

| Handle | Bytes | Result |
| --- | --- | --- |
| `open(p)` (text) | — | same as `loads(f.read())` |
| `open(p, 'rb')` | valid UTF-8 | identical to the text handle (US5.5) |
| `open(p, 'rb')` | invalid UTF-8 | `EncodingError` (US5.6) |
| `io.BytesIO(b'\xff\xfe')` | invalid | `EncodingError` |

**Invariant (FR-010, US5.6)**: no U+FFFD replacement character and no unpaired
surrogate appears in any result. `errors='replace'`, `errors='surrogateescape'`,
and `errors='ignore'` are all forbidden — §11.1 names them.

`filename` defaults to `file_obj.name` when present (§11.1); a `BytesIO` has no
`.name`, so `None` is the fallback.

### Positions from text handles are in newline-translated text

`open(p)` defaults to `newline=None`, so the handle has already turned `\r\n`
and `\r` into `\n` before `load` reads it. `load` sees no `\r`, and the
`Pos.index` values it reports on a CRLF file are offsets into the translated
text, not the file on disk that FR-013 targets. `line` and `column` still
agree with the file, because the translation is one break for one break.
`load` cannot recover the original, so this is documented rather than fixed:
`load`'s docstring and the FR-015 migration notes say that editor-grade
`Pos.index` values need a binary handle or `open(p, newline='')`.

| Handle over `b"a: b\r\nc: d"` | `Pos.index` of key `c` |
| --- | --- |
| `open(p, 'rb')` | 6 (on-disk offset) |
| `open(p, newline='')` | 6 |
| `open(p)` | 5 (translated text), `line` 2, `column` 0 |

### Why widen `load` rather than add `loadb`

Recorded in plan.md's Constitution Check under principle VI. In short: §11.1
puts the strict-decoding duty on `load` itself, and `open(path, 'rb')` handles
are what callers already have in hand. A second entry point would leave the
existing one silently non-conforming.

## `parse`

Returns the `Root` node. Callers use `.as_data()` (equivalent to `loads`) or
`.as_source()` (Contract 08). Same exception contract as `loads`.

## Test obligations

- Every table row above.
- A leaf-walking helper asserting the no-`None` invariant over every acceptance
  fixture.
- `load` with `StringIO`, `BytesIO`, a real text handle, and a real binary
  handle over the same content, asserting equal results.
- `filename` propagation into `Source.filename` and into `ParseError.message`.
- The three-handle table above over a real CRLF file on disk, pinning that
  `as_data()` is equal across all three while `Pos.index` differs for the
  default text handle.
- mypy strict accepts `load(open(p))` and `load(open(p, 'rb'))` without a cast.
