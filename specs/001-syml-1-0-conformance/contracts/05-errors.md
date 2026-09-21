# Contract 05 — The error taxonomy (§11.3)

**Requirements**: FR-009 | **User story**: US5
**Spec**: §8.1–§8.5, §11.3 | **Decisions**: D7, D10 (deferred)
**Audit gaps**: 11, 12 | **`todo.txt`**: B2, A3 (reversed on class), A4 (reversed on class)
**Research**: R-03 (attribute shape), R-04 (`EncodingError`), R-09 (the boundary)

## Surface

```python
# src/syml/exceptions.py

class ParseError(ValueError):
    message: str
    position: Pos
    line_text: str

    def __init__(self, message: str, position: Pos, line_text: str) -> None:
        super().__init__(message, position, line_text)
        self.message = message
        self.position = position
        self.line_text = line_text


class OutOfContextNodeError(ParseError): ...
class TabIndentationError(ParseError): ...
class EncodingError(ParseError): ...          # new; §11.3 amended (FR-009)


class DuplicateKeyError(ParseError):
    key: str
    first_position: Pos


class MalformedQuotedStringError(ParseError):
    escape: str | None
    code_point: int | None


class UnrepresentableValueError(ValueError):  # raised by dumps, NOT a ParseError
    ...
```

All seven are exported from `syml/__init__.py`. **`DocumentLimitError` is not**
— §13.4's limits are deferred past 1.0, and §11.3's class list and §13.4 are
edited to say so (spec Edge Cases). A caller must not expect an eighth class.

## Attribute contract (R-03)

`.position` is **always** a `Pos`, never `None`, never a bare line number.
`.line_text` is **always** a `str` — the empty string when the position is past
the last line. Both are present on every subclass. Positions are **original-text**
coordinates (FR-013, Contract 01's `PositionMap`).

`super().__init__(message, position, line_text)` preserves the existing `.args`
tuple, so current `except ParseError as e: e.args[1]` code keeps working while
gaining the named attributes §11.3 requires.

| Class | `position` anchors at | Extra attributes |
| --- | --- | --- |
| `OutOfContextNodeError` | the offending node's start | — |
| `DuplicateKeyError` | the repeated key's start | `key: str`, `first_position: Pos` (the first occurrence) |
| `TabIndentationError` | the **first tab** in the line's leading whitespace | — |
| `MalformedQuotedStringError` | the **opening quote** | `escape`, `code_point` (both `None` for unterminated / trailing-content) |
| `EncodingError` | the first invalid byte, converted to code points | — |

### `EncodingError` position derivation (R-04)

`UnicodeDecodeError.start` is a **byte** offset, not a code-point index.

1. `prefix = raw[: err.start].decode('utf-8')` — always succeeds (UTF-8 is
   self-synchronizing; `err.start` is a sequence boundary).
2. `index` = `len(prefix)` in code points.
3. `line` = 1 + line breaks in `prefix`, counting `\r\n`, bare `\r`, and `\n`
   each as one. (The raw text has not been normalized — it cannot be decoded.)
4. `column` = code points since the last break.
5. `line_text` = `prefix`'s final partial line. It is necessarily truncated at
   the bad byte; that is the contract.

These are original coordinates by construction; `PositionMap` is not involved.

## The third-party boundary (FR-009, R-09)

**No exception from Parsimonious may escape `loads`, `load`, or `parse`.**

Because parsing is per-line (Contract 02), a `parsimonious.exceptions.IncompleteParseError`
raised by `GRAMMAR['line'].parse(...)` means exactly one thing: *this line did
not fully lex*. With `data = ~"[^\n]*"` as the last alternative of every path,
the only way a line fails to fully lex is a `quoted_value` that closed and was
followed by non-whitespace — §4.7's trailing-content case. The boundary handler
therefore classifies it as `MalformedQuotedStringError`; there is no residual
"unknown parse failure" bucket.

Every call into Parsimonious is wrapped. `ParseError` and its subclasses stay in
`unwrapped_exceptions` so the tree builder's own raises pass through unwrapped.

| Input | Today | Spec |
| --- | --- | --- |
| `key:value` | `parsimonious.exceptions.IncompleteParseError` | scalar `"key:value"` (US5.2) |
| `key: "a" trailing` | — | `MalformedQuotedStringError` (US6.6) |
| `key:␠` | `IncompleteParseError` | `{"key": ""}` (US4.4) |

> `␠` marks a significant trailing space; the repository's pre-commit hook
> strips literal ones.

## Which error for which condition

| Condition | Class | Spec |
| --- | --- | --- |
| indentation fitting no sibling/child/parent level | `OutOfContextNodeError` | §8.1 |
| context violation (closed node, wrong type at a level) | `OutOfContextNodeError` | §8.2 |
| key repeated within one mapping | `DuplicateKeyError` | §8.3 |
| tab in a non-blank line's leading whitespace | `TabIndentationError` | §8.4, §9.0.3 |
| unterminated / trailing / bad escape / bad code point | `MalformedQuotedStringError` | §8.5, §4.7 |
| undecodable bytes from `load` | `EncodingError` | §11.1 |
| value with no SYML encoding | `UnrepresentableValueError` | §11.2.2–.4 |

D7 stands: §8.1 and §8.2 both raise `OutOfContextNodeError`; there is no
`InconsistentIndentationError` (`todo.txt` A4 is reversed on class).

## Test obligations

- All seven classes import from `syml` and their `__mro__` matches the tree
  above (US5.1).
- For each class, one triggering input asserting `message`, `position`,
  `line_text`, and any extra attributes.
- `DuplicateKeyError.first_position` points at the **first** occurrence (US5.4).
- `EncodingError` on a multi-byte prefix: `position.index` is a code-point
  index, not a byte offset. A fixture with a non-ASCII character before the bad
  byte is mandatory — this is the trap R-04 names.
- Sweep: every document in the audit's corpus plus every acceptance fixture,
  asserting that any exception raised is a `ParseError` (SC-005).
- Each of the seven classes is raised by at least one scenario (SC-005).
