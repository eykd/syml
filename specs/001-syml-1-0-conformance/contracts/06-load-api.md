# Contract 06 — `loads`, `load`, `parse` (§11.1, §11.2)

**Requirements**: FR-005, FR-009, FR-010 | **User stories**: US4, US5
**Spec**: §7.3, §7.4, §11.1, §11.2, §13.3 | **Audit gap**: 18 | **Research**: R-04

## Surface

```python
# src/syml/__init__.py  (SymlData and SymlInput are defined in basetypes.py
# and re-exported here: serializer.py needs them and precedes __init__.py in
# the import order, plan.md § Project Structure; red-team pass 20)

from .basetypes import SymlData, SymlInput  # re-exported through __all__ below; no noqa (RUF100)

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
| static return type | `list[Any] \| dict[str, Any] \| str` | `SymlData`: a typed caller's `r['k']['j']` after `isinstance(r, dict)` checked under 0.6.2 (`Any` below the top) and is a mypy error under 1.0.0 until each level is narrowed (**breaking for typed callers**, pass 20; plan.md Principle VI) |
| exceptions | Parsimonious may escape | only `ParseError` subclasses |

**`__init__.py` declares `__all__`** naming `loads`, `load`, `parse`, `dumps`,
`dump`, `SymlData`, `SymlInput`, and the seven exception classes (red-team
pass 21). pyproject sets mypy's `no_implicit_reexport = true`, and mypy covers
`tests/`, so without `__all__` (or `import X as X`) every
`from syml import DuplicateKeyError` in a test is a mypy error even though it
imports at run time.

`parse` is promoted from an internal in `syml.parsers` to a documented §11.2
export; it is the entry point for source tracking (Contract 08).

## `loads`

Applies Contract 01's pre-processing, Contract 02's per-line lexing, Contract
03's tree building, then `Root.as_data()`.

| Document | Result | Requirement |
| --- | --- | --- |
| `""` | `""` | FR-005, §7.4 (US4.2) |
| `"# just a comment"` | `""` | FR-005, §7.4 (US4.3) |
| `"\ufeff"` | `""` | FR-002 (US2.2) |
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
    if filename is None:                        # resolved FIRST, so EncodingError
        name = getattr(file_obj, 'name', None)  # can carry it (Contract 05 error_message)
        filename = name if isinstance(name, str | Path) else None   # pathlib.Path, pass 23
    try:
        raw = file_obj.read()                   # a text handle decodes here
    except UnicodeDecodeError as err:
        raise encoding_error(err, filename) from err   # Contract 05: R-04 over (object, start, encoding)
    if isinstance(raw, bytes):
        try:
            text = raw.decode('utf-8')          # strict: no errors= substitution
        except UnicodeDecodeError as err:
            raise encoding_error(err, filename) from err
    else:
        text = raw
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
| `open(p, encoding='utf-8')` (text) | invalid UTF-8 | `EncodingError` — not the `UnicodeDecodeError` that `read()` raises |
| `open(p, encoding='cp1252')` (text; also `open(p)` under a cp1252 locale) | UTF-8 `Á` (`C3 81`): `0x81` is undefined in cp1252 | `EncodingError` at the `0x81` — position derived with the handle's codec, so no second `UnicodeDecodeError` escapes (Contract 05, pass 18) |
| `open(p, encoding='cp1252')` (same) | UTF-8 `é` (`C3 A9`): both bytes are defined in cp1252 | **no error**: `{'key': 'Ã©'}`. The handle decoded, not `load`, so §11.1's strict-UTF-8 duty is not discharged on this path (pass 20, below) |

**§11.1's strict decoding is guaranteed on the bytes path only (red-team
pass 20).** `load` can decode strictly only when `read()` hands it bytes. A
text handle has already decoded with its own codec, and `load` sees only the
`str`. The `Á` row above fails because `0x81` happens to be undefined in
cp1252; the `é` row is the common case, and it loads as mojibake with no
error. `load` cannot detect that, so it is documented rather than prevented:
`load`'s docstring says that strict UTF-8 (§11.1, §13.3) needs a binary
handle or `encoding='utf-8'`, the same advice the newline table below gives
for positions, and Contract 09's migration note 11 says the same.

**Invariant (FR-010, US5.6)**: when `load` decodes bytes itself, it never
substitutes: no U+FFFD replacement character and no unpaired surrogate enters a
result that was not spelled in the input. `errors='replace'`,
`errors='surrogateescape'`, and `errors='ignore'` are all forbidden — §11.1
names them. The invariant is scoped to bytes `load` decodes: a valid UTF-8 file
may legitimately contain U+FFFD, and a caller's own text handle opened with
`errors='replace'` has substituted before `load` is called.

**Text handles over invalid bytes (red-team pass 5).** A text handle decodes
inside `read()`, so invalid bytes surface as `UnicodeDecodeError` from `load`'s
first line — a non-`ParseError` escaping `load`, which FR-009 forbids and which
disagrees with the `'rb'` row. `load` therefore wraps `read()` and raises
`EncodingError`. `TextIOWrapper.read()` with no size decodes everything from the
handle's position in one call, so `err.object` is those bytes and `err.start` a
byte offset into them; R-04's derivation (Contract 05) applies unchanged. Verified
on a 30 KB file: `err.object` is the whole file and `err.start` the offending
byte's file offset. The handle's codec need not be UTF-8, which is why the
derivation decodes the prefix with `err.encoding` rather than `'utf-8'`
(red-team pass 18): the prefix before a cp1252 failure can end in half a UTF-8
sequence. For such a handle the position counts the code points the handle
itself would have produced. `line_text` is in the failing codec's reading,
which for cp1252 is the generic `'charmap'` codec, so bytes 0x80-0x9F appear
as C1 controls (pass 19; positions are unaffected).
`encoding='utf-8-sig'` strips the mark before decoding, so its `err.object`
starts after the BOM and its `index` is one less than a binary handle's over
the same file. A handle already partly read reports positions relative to
where `read()` began — the same caveat as the newline table below.

`filename` defaults to `file_obj.name` when present (§11.1); a `BytesIO` has no
`.name`, so `None` is the fallback. `.name` is not always a path:
`tempfile.TemporaryFile()` and `open(fd)` expose an **int** file descriptor
(verified: `TemporaryFile('w+').name == 3`), and `getattr` hands mypy an `Any`,
so the type checker cannot catch it. Only a `str` or `os.PathLike` name is used;
anything else falls back to `None`, keeping `Source.filename` and every
`ParseError` message within `StrPath | None`.

**The check is `str | Path`, not `(str, os.PathLike)` (red-team pass 23).**
`StrPath` is `str | Path`, and `isinstance(name, os.PathLike)` narrows the
`Any` from `getattr` to `PathLike[Any]`, which mypy rejects as a
`StrPath | None` assignment (verified); ruff's `UP038` also rejects the
tuple form. Nothing is lost in practice: `open(Path(p)).name` is a `str`
(verified), so a non-`Path` `PathLike` name comes only from a custom
file-like, and falling back to `None` for it is the documented default.
Widening `StrPath` instead would widen `Source.filename`'s declared type, a
typing change on the semver-guarded `Source`.

### Positions from text handles are in newline-translated text

`open(p)` defaults to `newline=None`, so the handle has already turned `\r\n`
and `\r` into `\n` before `load` reads it. `load` sees no `\r`, and the
`Pos.index` values it reports on a CRLF file are offsets into the translated
text, not the file on disk that FR-013 targets. `line` and `column` still
agree with the file, because the translation is one break for one break.
`load` cannot recover the original, so this is documented rather than fixed:
`load`'s docstring and the FR-015 migration notes say that editor-grade
`Pos.index` values need a binary handle or `open(p, encoding='utf-8',
newline='')` — the explicit encoding matters too, because the locale default is
not UTF-8 everywhere (Windows before Python 3.15).

| Handle over `b"a: b\r\nc: d"` | `Pos.index` of key `c` |
| --- | --- |
| `open(p, 'rb')` | 6 (code-point offset into the decoded file; equals the byte offset only for ASCII) |
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
- `filename` propagation into `Source.filename` and into `ParseError.message`
  (Contract 05's `error_message`), including `EncodingError` from a named
  binary handle; with no filename the message is the bare description.
- A handle whose `.name` is an `int` (`tempfile.TemporaryFile`) yields
  `Source.filename is None`.
- A UTF-8 text handle (`encoding='utf-8'`, not `'utf-8-sig'`) over invalid
  bytes raises `EncodingError` (not `UnicodeDecodeError`) with the same `Pos`
  as the binary handle over the same file.
- A cp1252 text handle over UTF-8 `key: Á` raises `EncodingError`, and no
  `UnicodeDecodeError` escapes `load` (Contract 05's derivation, pass 18).
- A cp1252 text handle over UTF-8 `key: é` returns `{'key': 'Ã©'}` with no
  error, while a binary handle over the same bytes returns `{'key': 'é'}`.
  This pins the documented limit of the text path (pass 20), so a future
  change to it is a visible diff.
- The three-handle table above over a real CRLF file on disk, pinning that
  `as_data()` is equal across all three while `Pos.index` differs for the
  default text handle.
- mypy strict accepts `load(open(p))` and `load(open(p, 'rb'))` without a cast.
- Fake handles in these tests subclass `io.StringIO` or `io.BytesIO` and
  override `read`, so they satisfy `IO[str] | IO[bytes]`; a bare class with a
  `read` method is an `arg-type` error in the mypy-checked test module
  (verified, pass 23).
