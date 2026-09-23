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
followed by anything other than a run of ASCII spaces (`~" *"`, §4.1) —
§4.7's trailing-content case. This is ASCII space specifically, not D15
`White_Space`: a tab or other Unicode whitespace character right after the
closing quote also strands the line and gets the same classification. The
boundary handler therefore classifies it as `MalformedQuotedStringError`;
there is no residual "unknown parse failure" bucket.

### Detecting the stranding and anchoring at the opening quote

`IncompleteParseError.pos` is the **strand point** (the character after the
closing quote and any ASCII spaces), not the opening quote this contract's
anchor table requires — and nothing in the exception names the quote. So the
entry point does **not** call `parse()` and catch `IncompleteParseError`. It
calls `GRAMMAR['line'].match(line.text)`, which returns the prefix's parse tree
without the full-consumption check (`parse` is `match` plus that check;
verified 2026-09-23 that `IncompleteParseError.pos == match(...).end`):

```python
pnode = GRAMMAR['line'].match(line.text)
if pnode.end < len(line.text):                       # stranded: §4.7 trailing content
    quote = find_first(pnode, 'quoted_value')        # exactly one on this path
    raise MalformedQuotedStringError(
        message, doc.position_map.to_original(pos_at(quote.start + line.start)),
        line_text, escape=None, code_point=None,
    )
node = visitor.visit(pnode, line)
```

- **Exactly one `quoted_value`** is in a stranded prefix: the grammar admits a
  quoted value only in `key_value`'s first alternative and `value`'s second,
  each followed only by `~" *"`, and inline nesting forms a single chain. The
  lookup is therefore unconditional — no "not found" branch, no pragma.
- **`match` cannot raise `parsimonious.exceptions.ParseError`** for a line:
  `data = ~"[^\n]*"` matches the empty string, so some alternative always
  matches. No `except` clause is written for it.
- **Precedence**: the stranding check runs **before** the line is visited, so
  a line that is both stranded and carries an out-of-range escape
  (`k: "\ud800" x`) is classified as trailing content (`escape=None`,
  `code_point=None`). Both anchor at the same opening quote; the rule just
  pins which attributes the caller sees.
- The R-09 fuzz corpus (red-team open item 1) becomes a regression test
  asserting, for every stranded line, that the prefix contains exactly one
  `quoted_value` and that `pnode.end` sits after its closing quote plus ASCII
  spaces only.

### Other Parsimonious exceptions

`ParseError` and its subclasses stay in `unwrapped_exceptions` so the visitor's
own raises (the quote-guard, decode errors) pass through unwrapped.
Parsimonious wraps **every other** exception raised inside a `visit_*` method in
`parsimonious.exceptions.VisitationError` — which would be a Parsimonious
exception escaping `loads`. Two rules close that:

1. `unwrapped_exceptions = (ParseError, RecursionError)`, so a recursion
   overflow while visiting a deeply nested inline line surfaces as the host
   `RecursionError` — the documented known limitation — not as
   `VisitationError`.
2. Tree incorporation (`incorporate_node`, Contract 03) runs in the per-line
   loop, **outside** `NodeVisitor.visit`, so its raises are never wrapped.

### `line_text`

`line_text` is the **original** physical line containing `position`, without
its terminator (`\r\n`, `\r`, or `\n`), and including a leading U+FEFF on
line 1 when the document had one. Taking it from the original text (not the
normalized line) is what makes `line_text[position.column]` the offending
character on every line, including a BOM-bearing line 1, whose column is
shifted by one (Contract 01). It is the empty string when `position` is past
the last line.

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
- For every `ParseError` raised from a parsed line (all classes except
  `EncodingError`), `e.line_text[e.position.column]` is the anchor character
  named in the attribute table — asserted on LF, CRLF, and BOM-bearing inputs.
- `MalformedQuotedStringError` for `key: "a" trailing`, `- k: 'it''s' x`, and
  `k: "a"\tx` has `position.column` at the **opening** quote (5, 5, 3), not at
  the strand point.
- A single line of inline list markers deep enough to exhaust the recursion
  limit (`'- ' * 200 + 'x'` at the default limit) raises the host
  `RecursionError`, never `VisitationError` or any other
  `parsimonious.exceptions` class.
- `EncodingError` on a multi-byte prefix: `position.index` is a code-point
  index, not a byte offset. A fixture with a non-ASCII character before the bad
  byte is mandatory — this is the trap R-04 names.
- Sweep: every document in the audit's corpus plus every acceptance fixture,
  asserting that any exception raised is a `ParseError` (SC-005).
- Each of the seven classes is raised by at least one scenario (SC-005).
