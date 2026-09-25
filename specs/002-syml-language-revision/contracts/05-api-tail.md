# Contract 05 — The API Tail: Input Types, Filenames, Blank-Document Positions, §11.3

**Requirements**: FR-017, FR-014 (documentation half) | **Findings closed**: `syml-xreq.7`, `.11`, `.13`, `.14`, `.23` (docs half) | **Research**: R-10

## Surface

```python
def loads(document: str, filename: StrPath | None = None) -> SymlData: ...
def load(file_obj: IO[str] | IO[bytes], filename: StrPath | None = None) -> SymlData: ...
```

Signatures unchanged. `syml.__all__` unchanged (no `DocumentLimitError`).

## Behaviour

| Input | Result |
| --- | --- |
| `loads(b"k: v")` | `TypeError`, message names `str` and `bytes` (e.g. `loads() expects str, not bytes`) |
| `loads(None)` / `loads(1)` | `TypeError` naming the received type |
| `load(h)` where `h.read()` returns `bytes` | decoded as strict UTF-8 (unchanged); invalid → `EncodingError` |
| `load(h)` where `h.read()` returns a `memoryview` | `TypeError` (`load() expects file_obj.read() to return str or bytes, not memoryview`) |
| `load(h)` on a closed `io.StringIO` | `TypeError`, chained `from` the `ValueError`; `except ParseError` does not catch it |
| `load(h)` with `h.name = pathlib.PurePosixPath("p.syml")` and a duplicate key | `.message` begins `p.syml: ` |
| `load(h)` with a custom `os.PathLike` name | its `os.fspath`, decoded with `os.fsdecode`, is the filename |
| `load(h)` with `h.name` an `int` or `bytes` | no filename (unchanged) |
| `load(h)` with `h.name = pathlib.PurePosixPath(os.fsdecode(b"\xff.syml"))` and a duplicate key | `.message` begins `\udcff.syml: ` (raw); `str(e)` begins `\\udcff.syml:` (escaped by `_printable`, Contract 03) and encodes to UTF-8 |
| `parse("\n").as_source().start` | `Pos(index=1, line=2, column=0)` |
| `parse("# x\n").as_source().start` | `Pos(index=4, line=2, column=0)` (a comment-only document is zero-width again under the column-0 comment rule, R-18; this is `syml-xreq.11`'s original input) |
| `parse("").as_source().start` | `Pos(index=0, line=1, column=0)` (unchanged) |

Order inside `load`: resolve the filename; call `read()`; a
`UnicodeDecodeError` becomes `EncodingError` (unchanged); any other
`ValueError` from `read()` becomes `TypeError`; then check the result's type;
then decode bytes; then `loads`.

`Pos.from_str_index(text, index)`: when `index == len(text)` and `text` ends
with `\n`, the position is `(index, text.count("\n") + 1, 0)`. Every other index
is unchanged.

## Specification and documentation

- §11.3 lists `EncodingError(ParseError)` (invalid UTF-8 from `load`, §11.1)
  and moves `DocumentLimitError` to a closing paragraph: "Implementations that
  enforce §13.4's limits SHOULD raise `DocumentLimitError(ParseError)`; `syml`
  enforces none and does not define it." The "MUST expose these exact class
  names" sentence then applies to the classes listed above it.
- §8.5 and §13.4 say the same (limits are recommendations; `syml` documents
  its recursion cliff instead, Contract 06).
- The README's `Source` paragraph (FR-014) states: `Source` is not a `str`
  subclass (it compares and hashes like its text, and `str(source)` gives the
  text); an empty `Source` is truthy and has no `len()`; a multi-line
  `Source.text` is the dedented value `as_data()` returns, paragraph breaks
  included, not a slice of the original document. The same three facts go in
  `Source`'s class docstring.

## Test obligations

1. Every row above.
2. A test compares §11.3's class list with the exception classes in
   `syml.__all__` (US4 scenario 6).
3. `Pos.from_str_index` at the end of `"a\n"`, `"\n"`, `"a"`, `""`.
