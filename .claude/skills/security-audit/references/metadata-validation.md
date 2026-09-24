# Untrusted Input & File Handling Validation

## Purpose

`syml.load(file_obj, filename=None)` and `syml.loads(text, filename=None)`
are the two points where untrusted data crosses into the parser. Neither
takes a raw filesystem path, which removes a whole class of path-traversal
bugs — but the encoding, size, and metadata (`filename`) a caller supplies
still need validation before and during parsing.

## Critical Validation Points

### 1. Encoding Validation

#### Why It Matters

`syml.load` reads from a file-like object. If the caller opened that file
with the wrong encoding (or none at all, in binary mode), decoding errors
or silent mojibake can reach the grammar as malformed text, producing
confusing `ParseError`s or, worse, changing the meaning of parsed values
without erroring at all.

#### Implementation

```python
from pathlib import Path

import syml


def load_syml_file(path: Path) -> dict[str, object]:
    """Load a SYML file, failing loudly on encoding problems."""
    with path.open("r", encoding="utf-8", errors="strict") as f:
        return syml.load(f, filename=str(path))
```

```python
# ❌ Wrong — binary mode silently hands bytes where str is expected,
# or errors="replace" hides corruption instead of surfacing it.
with path.open("rb") as f:
    data = syml.load(f, filename=str(path))  # type error / garbage in, garbage out
```

#### Recommended Defaults

- Always open text files as UTF-8 with `errors="strict"` unless the caller
  has a documented reason to support another encoding
- Never pass `errors="replace"` or `errors="ignore"` for untrusted input —
  silently substituting characters can change which key/value a line parses
  as without raising

### 2. Input Size Validation

#### Why It Matters

Nothing in `syml.loads`/`syml.load` currently bounds how much text it will
accept. A caller that reads an entire untrusted file into memory before
calling `loads`, or that hands `load` a file-like object over an unbounded
stream, can be driven to exhaust memory by a single oversized document.

#### Implementation

```python
MAX_SYML_BYTES = 5 * 1024 * 1024  # 5 MiB — tune to the caller's domain


def read_bounded(file_obj: object, max_bytes: int = MAX_SYML_BYTES) -> str:
    """Read at most max_bytes+1 to detect (not silently truncate) oversize input."""
    data = file_obj.read(max_bytes + 1)  # type: ignore[attr-defined]
    if len(data) > max_bytes:
        raise ValueError(f"input exceeds {max_bytes} byte limit")
    return data
```

#### Recommended Size Limits

Tune to the deployment, but as a starting point for a config-file format:

- Interactive/CLI use: no hard limit needed, but log a warning above ~1 MB
- Service ingesting untrusted uploads: 1-10 MiB depending on domain
- Batch/CI config parsing: bound by the repo's own file-size conventions

### 3. `filename` Metadata Handling

#### Why It Matters

`filename` is advisory: it is embedded into `Source`/`Pos` objects for
error messages and equality/hashing, and is never used by the library to
open, resolve, or traverse a filesystem path. That means the classic
path-traversal risk (`../../etc/passwd`) does not apply *inside* the
library — but a caller that builds a **display or log message** from an
attacker-supplied `filename` value can still leak more path information
than intended, or allow control-character injection into terminal/log
output.

#### Implementation

```python
import re

_UNSAFE_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_filename_for_display(filename: str) -> str:
    """Strip control characters before echoing an untrusted filename back."""
    return _UNSAFE_CONTROL_CHARS.sub("", filename)
```

```python
# ❌ Wrong — echoes a caller-controlled filename straight into a log line,
# letting it inject ANSI escapes or spoof adjacent log entries.
logger.info("parsed %s", filename)

# ✅ Correct — sanitize before it reaches a terminal or log aggregator.
logger.info("parsed %s", sanitize_filename_for_display(filename))
```

#### Recommended Practice

- Treat `filename` as untrusted display text if it originates from a
  network request or another service, not just as an internal identifier
- Never use `filename` to construct a filesystem path for a *second* file
  operation (e.g. writing a cache/output file) without independent
  validation — that reintroduces path traversal at the call site even
  though the library itself never does this

### 4. Document Shape Validation (Depth & Line Count)

Covered in detail in [rate-limiting.md](rate-limiting.md): deeply nested or
extremely long documents are a resource-exhaustion concern, not a metadata
one, but they are validated at the same boundary (before/during `load`) as
encoding and size.

## Validation Pipeline Pattern

```python
from pathlib import Path

import syml


def load_untrusted_syml(path: Path, max_bytes: int = MAX_SYML_BYTES) -> dict[str, object]:
    """Full validation pipeline for an untrusted SYML file."""
    if not path.is_file():
        raise ValueError(f"not a regular file: {path}")

    with path.open("r", encoding="utf-8", errors="strict") as f:
        text = read_bounded(f, max_bytes)

    return syml.loads(text, filename=sanitize_filename_for_display(str(path)))
```

## Testing Untrusted Input Handling

### Test Encoding Validation

```python
import pytest

import syml


def test_it_should_raise_on_invalid_utf8_bytes(tmp_path) -> None:
    bad_file = tmp_path / "bad.syml"
    bad_file.write_bytes(b"key: \xff\xfe not valid utf-8")

    with pytest.raises(UnicodeDecodeError):
        with bad_file.open("r", encoding="utf-8", errors="strict") as f:
            syml.load(f, filename=str(bad_file))
```

### Test Size Validation

```python
def test_it_should_reject_input_beyond_the_configured_byte_limit() -> None:
    oversized = ("key: value\n" * 1_000_000)

    with pytest.raises(ValueError, match="exceeds"):
        read_bounded(io.StringIO(oversized), max_bytes=1024)
```

### Test Filename Sanitization

```python
def test_it_should_strip_control_characters_from_filename() -> None:
    dirty = "report\x1b[31m.syml"
    assert sanitize_filename_for_display(dirty) == "report[31m.syml"
```

## Best Practices Checklist

- [ ] Files are opened with an explicit, strict encoding — never silent
      `errors="replace"`/`errors="ignore"` for untrusted input
- [ ] Input is read with an enforced size cap before being handed to `loads`
- [ ] `filename` is treated as untrusted display text at any boundary where
      it reaches logs, terminals, or HTML/response bodies
- [ ] `filename` is never reused to open a *different* file without its own
      independent validation
- [ ] Nesting depth and line count are bounded per [rate-limiting.md](rate-limiting.md)

## Common Vulnerabilities

### ❌ Reading Untrusted Input Without a Size Check

```python
text = untrusted_stream.read()  # unbounded — memory-exhaustion risk
syml.loads(text)
```

### ✅ Validate Size Before Reading Fully

```python
text = read_bounded(untrusted_stream, max_bytes=MAX_SYML_BYTES)
syml.loads(text)
```

### ❌ Echoing `filename` Straight Into Logs or Responses

```python
print(f"Failed to parse {filename}")  # filename may contain control chars
```

### ✅ Sanitize Before Display

```python
print(f"Failed to parse {sanitize_filename_for_display(filename)}")
```

### ❌ Reusing an Untrusted `filename` for a Second File Operation

```python
# filename came from a SYML document's own metadata or a request param —
# using it to open a second file reintroduces path traversal at this call
# site, even though syml itself never does this.
with open(filename) as f:
    ...
```

### ✅ Validate Independently Before Any Second File Operation

```python
safe_path = (TRUSTED_BASE_DIR / Path(filename).name).resolve()
if not safe_path.is_relative_to(TRUSTED_BASE_DIR):
    raise ValueError("invalid filename")
with safe_path.open() as f:
    ...
```

## Related Skills

- **security-audit**: Full taxonomy (untrusted input, recursion, ReDoS, file handling)
- **rate-limiting.md**: Resource-exhaustion limits for the same input boundary
