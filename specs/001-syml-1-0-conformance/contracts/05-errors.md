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

    def __init__(
        self, message: str, position: Pos, line_text: str, *extra: object
    ) -> None:
        super().__init__(message, position, line_text, *extra)   # .args: pickle/copy rebuild from it
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

**`message` carries the filename (red-team pass 14).** `ParseError` has no
`filename` attribute and neither has `Pos`, so the message is the only place a
caller learns which file failed (data-model §1). Every raise site builds its
message with one helper:

```python
def error_message(description: str, filename: StrPath | None) -> str:
    """`description` alone when filename is None, else f'{filename}: {description}'."""
```

`error_message` lives in `exceptions.py`, which imports nothing from the
rest of `syml` at run time (plan.md § Project Structure, module homes).
`description` is the fixed text each raise site names below
(`'Failed to incorporate a node'`, `'Duplicate key'`, and so on). The parsed-line
sites pass `doc.filename`, `preprocess` passes its own `filename` argument, and
`load` passes the filename it resolved before calling `read()` (Contract 06).

`super().__init__(message, position, line_text, *extra)` preserves the
existing `.args` prefix, so current `except ParseError as e: e.args[1]` code
keeps working while gaining the named attributes §11.3 requires. The two
subclasses with extra attributes append them to `.args` (§ Subclass
constructors, red-team pass 18).

| Class | `position` anchors at | Extra attributes |
| --- | --- | --- |
| `OutOfContextNodeError` | the offending node's start | — |
| `DuplicateKeyError` | the repeated key's start | `key: str`, `first_position: Pos` (the first occurrence) |
| `TabIndentationError` | the **first tab** in the line's leading whitespace | — |
| `MalformedQuotedStringError` | the **opening quote** | `escape`, `code_point` (both `None` for unterminated / trailing-content) |
| `EncodingError` | the first invalid byte, converted to code points | — |

### `EncodingError` position derivation (R-04)

`UnicodeDecodeError.start` is a **byte** offset, not a code-point index.

1. `prefix = err.object[: err.start].decode(err.encoding, errors='replace')`
   — decoded with **the codec that failed**, not with a hard-coded `'utf-8'`
   (red-team pass 18). The derivation is over `(err.object, err.start,
   err.encoding)` alone and does not depend on where the bytes came from — a
   binary handle, or (Contract 06) the bytes a text handle's `read()` decoded
   internally. That codec decoded exactly `err.object[:err.start]` without
   error before it stopped, so `errors='replace'` never substitutes on a real
   decode failure; it is an argument, not a branch, and it guarantees this
   step cannot raise a second `UnicodeDecodeError` from inside `load`'s own
   handler. For `load`'s own strict decode `err.encoding` is `'utf-8'`, and
   the result is exactly the UTF-8 prefix (UTF-8 is self-synchronizing and
   `err.start` is a sequence boundary).

   **Why not `.decode('utf-8')`.** A text handle decodes with *its* encoding,
   and `open(p)` uses the locale's, which is not UTF-8 everywhere (Contract
   06: Windows before Python 3.15). Over a UTF-8 file containing `Á`
   (`C3 81`), a cp1252 handle's `read()` raises `UnicodeDecodeError('charmap',
   …, start=6)` at the undefined byte `0x81`, so the prefix ends with the lone
   lead byte `0xC3`. Decoding that prefix as UTF-8 raises a second
   `UnicodeDecodeError` inside `load`'s `except` clause, and a
   non-`ParseError` escapes `load` (FR-009). Verified, together with a
   `utf-16-le` handle whose prefix is invalid UTF-8. With the failing codec
   both derive a position and raise `EncodingError`.
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
def find_first(node: Node, expr_name: str) -> Node:
    """Depth-first search of `node` and its descendants for the first one
    whose `expr_name == expr_name` (parsimonious `Node` has no such method;
    this contract defines it). `raise_trailing_content` calls it with
    `'quoted_value'`, and exactly one such node exists on that path, so the
    search always finds a match — there is no not-found case to handle."""


def original_line(doc: Document, n: int) -> str:
    """Line `n` (1-indexed, matching `Pos.line`) of `doc.original` — the
    UNNORMALIZED text — split by the same single-pass `\r\n|\r|\n` regex
    alternation Contract 01 uses for normalization (never `str.splitlines()`,
    which also breaks on U+2028/U+0085 and is forbidden by name, §13.3), with
    the terminator excluded. This is the `line_text` rule below (§
    `line_text`), taken from the original text so a leading BOM on line 1 is
    preserved. Empty string when `n` is past the last line."""


def raise_trailing_content(pnode: Node, line: Line, doc: Document) -> NoReturn:
    """The helper Contract 02's entry point calls when `pnode.end < len(line.text)`."""
    quote = find_first(pnode, 'quoted_value')         # exactly one on this path
    position = doc.position_map.to_original(pos_at(line, quote.start))  # Contract 01
    raise MalformedQuotedStringError(
        error_message('Unexpected content after quoted value', doc.filename),
        position, original_line(doc, position.line),
        escape=None, code_point=None,
    )

pnode = GRAMMAR['line'].match(line.text)
if pnode.end < len(line.text):                       # stranded: §4.7 trailing content
    raise_trailing_content(pnode, line, doc)
```

`pnode` offsets are **line-local** (per-line `match`), so `quote.start` goes
through `pos_at(line, …)` — never `quote.start + line.start` alone, which is an
index with no line or column. `find_first` and `original_line` are defined
above; neither is provided by parsimonious or Contract 01. Every raise site
uses the same two helpers. Homes (red-team pass 17): `original_line` in
`preprocess.py`, beside the normalization regex it must share and importable
by `nodes.py` without a cycle; `find_first` and `raise_trailing_content` in
`parsers.py`, which alone calls them.

### Subclass constructors

The subclasses with extra attributes take them as **ordinary positional-or-keyword**
parameters after the three base ones, with no defaults, and pass all five to
`super().__init__` so they land in `.args`:

```python
MalformedQuotedStringError(message, position, line_text, escape, code_point)
DuplicateKeyError(message, position, line_text, key, first_position)

class DuplicateKeyError(ParseError):
    def __init__(self, message: str, position: Pos, line_text: str,
                 key: str, first_position: Pos) -> None:
        super().__init__(message, position, line_text, key, first_position)
        self.key = key
        self.first_position = first_position
```

Every raise site still passes the extras by keyword (`key=…, first_position=…`,
`escape=…, code_point=…`), which reads the same as before.

**Why not keyword-only (red-team pass 18, correcting pass 7).** Pass 7 made the
extras keyword-only to keep `.args` at three elements. But `pickle` and
`copy.copy`/`copy.deepcopy` rebuild an exception through
`BaseException.__reduce__`, which is `(type(self), self.args, self.__dict__)`:
the class is called as `cls(*self.args)`. With keyword-only extras that call is
`DuplicateKeyError(message, position, line_text)`, a `TypeError` (verified on
both classes, for `pickle.loads(pickle.dumps(e))` and `copy.copy(e)`). So a
`DuplicateKeyError` or `MalformedQuotedStringError` raised in a
`ProcessPoolExecutor` or `multiprocessing` worker could not reach the parent
process, and `copy.copy(e)` failed. With the extras in `.args` all three
round-trips return an equal exception (verified). `e.args[1]` is still the
`Pos`, which is the compatibility §11.3 and plan.md's Constitution Check
promise; `len(e.args)` was never promised. A custom `__reduce__` would also
work, but it is one more method to cover and nothing needs the three-element
shape.

### Decoder failures cross the visitor as `ParseError`s

Contract 04's `decode_double_quoted(raw)` is position-free, so it cannot build
a `MalformedQuotedStringError` (whose `.position` is never `None`). It raises a
module-private `QuotedStringDefect(ValueError)` carrying `escape` and
`code_point`. The method that **calls the decoder** catches it and re-raises
`MalformedQuotedStringError`, anchored at the opening quote. That method is
`visit_quoted_value`, which builds the quoted `TextLeafNode` (Contract 02 §
Who sets `level`) and so is the only place the decoded text is needed:

```python
def visit_quoted_value(self, node: Node, children: list[Any]) -> TextLeafNode:
    raw = node.text                                  # quotes included (Contract 04)
    position = self.doc.position_map.to_original(pos_at(self.line, node.start))
    try:
        text = (decode_single_quoted(raw) if raw[0] == "'"
                else decode_double_quoted(raw))
    except QuotedStringDefect as defect:            # converted HERE, not in a parent
        raise MalformedQuotedStringError(
            error_message('Malformed quoted string', self.doc.filename),
            position, original_line(self.doc, position.line),
            escape=defect.escape, code_point=defect.code_point,
        ) from defect
    source = Source.from_node(node, self.line, self.doc.position_map, self.doc.filename)
    return TextLeafNode(pnode=node, level=node.start, quoted=True, inline=True,
                        source=dataclasses.replace(source, text=text))  # decoded text (Contract 08)
```

**Why not in `visit_key_value` / `visit_list_item` (red-team pass 17).**
Parsimonious's `NodeVisitor.visit` evaluates `method(node, [self.visit(n) for
n in node])`: every child is visited, and any child exception wrapped, **before**
the parent's method body runs. A `QuotedStringDefect` leaving
`visit_quoted_value` is therefore wrapped in `VisitationError` by the child's
own `visit` frame, and a `try`/`except` in `visit_key_value` never executes
(verified: with the catch in the parent, `k: "\ud800"`, `- "\ud800"`, and
`- - k: "\U00110000"` all escape as `parsimonious.exceptions.VisitationError`,
and neither parent method runs; with the catch in `visit_quoted_value`, all
three surface as the `ParseError` subclass). `QuotedStringDefect` is **not**
added to `unwrapped_exceptions`: that would let a private class escape `loads`
whenever the conversion is missed.

The quote-guard (Contract 04) is unaffected. It raises
`MalformedQuotedStringError` directly from `visit_key_value` /
`visit_list_item`, and a `ParseError` passes every enclosing `visit` frame
unwrapped.

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
2. Line-to-line tree incorporation (`incorporate_node`, Contract 03) runs in
   the per-line loop, **outside** `NodeVisitor.visit`. Each visit that builds a
   value-holding container attaches its own child the same way, still
   **inside** the visit: `visit_key_value` takes the empty `KeyValue` its
   `key_colon` child built (there is no `section` child on this path —
   `section` only matches a valueless line) and calls
   `section.incorporate_node(value, self.doc)` on it, and
   `visit_list_item` builds an empty `li` (`ListItem`) and calls
   `li.incorporate_node(value, self.doc)` — uniformly, whether `value` is a
   leaf (`TextLeafNode`) or, for `list_item`'s inline nesting (`- key: v`,
   `- - x`), itself a `structure` needing §9.2's full walk-up/auto-wrap
   algorithm. (`key_value`'s own value slot is never a `structure` — its
   grammar alternatives are only `quoted_value` or `data` — so `section`'s
   call always resolves in one step; `li`'s can recurse.) Two exceptions to
   "uniformly": a zero-length **unquoted** leaf value is not incorporated at
   all (D6, Contract 02 § Zero-length inline values), and neither call can
   see a `None` level, because every operand's `level` is set at
   construction (Contract 02 § Who sets `level`) — a `None` reaching `>` would
   be a `TypeError`, which is **not** in `unwrapped_exceptions`. That is safe
   because everything either call can raise is a `ParseError` or a
   `RecursionError`, and both are in `unwrapped_exceptions` (rule 1).

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
- The decoder rows (`\ud800` and `\U00110000`) at a `key:` position, after
  `- `, and nested as `- - k:` each raise `MalformedQuotedStringError` with
  `code_point` set and `position.column` at the opening quote, and nothing from
  `parsimonious.exceptions` (red-team pass 17: the conversion site).
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
- `EncodingError`, never `UnicodeDecodeError`, from `load` over a text handle
  whose encoding is not UTF-8: `io.TextIOWrapper(io.BytesIO('key: Á\n'.encode()),
  encoding='cp1252')` (position index 6, line 1, column 6, `line_text`
  `'key: Ã'`), and a `utf-16-le` handle over bytes that are invalid UTF-8
  (pass 18).
- Every class survives `pickle.loads(pickle.dumps(e))`, `copy.copy(e)`, and
  `copy.deepcopy(e)` with equal type, `.args`, and attributes (pass 18);
  `e.args[1]` is the `Pos` on every class.
- Sweep: every document in the audit's corpus plus every acceptance fixture,
  asserting that any exception raised is a `ParseError` (SC-005).
- Each of the seven classes is raised by at least one scenario (SC-005).
