# Glossary

Ubiquitous-language terms used across `syml`'s source and docs. The
`/glossary` skill maintains this file — it flags naming inconsistencies and
new domain concepts against the definitions below, so keep entries short and
update them here rather than letting a second name for the same concept
spread through the codebase.

- **Line node** — the result of lexing one line of SYML text in
  `src/syml/parsers.py`; every line lexes independently as
  `indent (comment / blank / structure / data) &eol`. `data` (not `value`) is
  the fallback alternative reached by a bare line or continuation line;
  quoting (`quoted_value`) is recognized only at the two dedicated inline
  positions reached through `structure` — after `key:` (`quoted_key_value`)
  and after `- ` (`value_list_item`, via `value`) — never on a standalone
  line.

- **Indentation level** — a node's own column (§4.1, R-11): each `SymlNode`
  computes `self.level` from its own `source.start.column` in
  `SymlNode.__post_init__`, not from a per-line tag inherited from the
  physical line it sits on.

- **`incorporate_node`** — the tree-building step (§9.2) that walks up the
  parent chain from the current tip, at each ancestor calling `can_add_node`
  to test acceptance; the climb continues node-by-node until some ancestor
  accepts, not by comparing indentation levels directly.

- **`can_add_node`** — the per-node predicate `incorporate_node` calls while
  climbing the parent chain. No longer just a plain container-vs-level check:
  `Mapping.can_add_node` raises `DuplicateKeyError` (§8.3) for a same-level
  sibling `KeyValue` that repeats an already-incorporated key, rather than
  falling through to §9.2's ordinary walk-up; a repeat at a different level
  is not caught here and falls through as usual. `TextLeafNode.can_add_node`
  tests the continuation baseline (or, while the baseline is still open, the
  anchor level) rather than any fixed container rule.

- **`ContainerNode`** — the base class of `Root`, `KeyValue`, and `ListItem`;
  it auto-inserts a `Mapping` or `List` intermediary when it receives a bare
  `KeyValue` or `ListItem` (§9.4), and fixes a newly-attached `TextLeafNode`'s
  `anchor_level`/`baseline` in `add_node`.

- **`TextLeafNode`** — a node carrying `inline`, `quoted`, `anchor_level`, and
  `baseline`. It declines more than it accepts: a quoted value accepts no
  continuation at all; otherwise `can_add_node` compares the candidate's level
  against the baseline once fixed, or against the anchor level while the
  baseline is still open (D11). Multiline scalar values accumulate only
  through nodes this logic admits, not through every following
  `TextLeafNode`.

- **`Source`** — a value type from `src/syml/basetypes.py` carrying filename
  plus start/end `Pos`; it compares and hashes by its text, so it works
  interchangeably with plain strings as dict keys.

- **`Pos`** — a position marker (index, line, column), built during parsing
  against the preprocessed (normalized) text. `PositionMap.to_original`/
  `to_original_source` translate a `Pos`/`Source` back to the caller's
  **original** text — before BOM stripping and CRLF/CR normalization (§9.0,
  FR-013). `SymlParser` applies this to the `Source` it builds for each
  parsed text leaf and key (`visit_text`, `visit_quoted_value`,
  `KeyLeafNode`), so those positions are in original-document coordinates;
  a container node's own `Source` and a raw error position built straight
  from `pnode.full_text` (e.g. `OutOfContextNodeError`'s) are not translated
  and stay in normalized-text coordinates.

- **`OutOfContextNodeError`** — raised when no ancestor in the parent chain
  accepts an incoming node; a subclass of `ParseError` (itself a
  `ValueError`). `unwrapped_exceptions` names `(ParseError, RecursionError)`,
  so every `ParseError` subclass — not just this one — passes the
  Parsimonious visitor unwrapped, and a host `RecursionError` raised from
  inside a `visit_*` method surfaces as itself rather than being re-wrapped
  as `parsimonious.exceptions.VisitationError` (Contract 05 §Other
  Parsimonious exceptions).

- **`as_data()`** — the rendering on every node that returns plain
  `str`/`list`/`dict` values, discarding source position information.

- **`as_source()`** — the rendering on every node that returns `Source`
  objects instead of plain strings, preserving filename and position.

- **Pre-processing** — the §9.0 pass that runs on the raw document before any
  grammar rule sees a line: strip one leading byte-order mark, normalize CRLF
  and bare CR to a line feed, and raise `TabIndentationError` for a tab in a
  non-blank line's leading whitespace.

- **Inline value** — text following a key's colon or a list item's hyphen on
  the same line (§4.6), as opposed to a block value written on the lines below.

- **Inline position** — the slot immediately after `key:` or `- ` on a line.
  It is the only place a quoted value is recognized (§4.7); a leading quote
  character anywhere else is ordinary text.

- **Block value** — a value written on the lines after a bare `key:` or `-`,
  indented deeper than the key or marker (§4.6). Unlike an inline value, its
  first line already occupies a line of its own and so sets the baseline
  immediately.

- **Continuation line** — a physical line accepted as part of an already-open
  multiline value. It must be indented deeper than the containing key-value
  pair or list item (−1 for a root scalar), and it is joined to the value with
  a line feed (§5.1).

- **Baseline** — the indentation of the first line of a multiline value that
  occupies a line of its own: an inline value's first continuation line, a
  block value's first block line, or 0 for a root scalar (§5.3, D11). Lines at
  or beyond the baseline join, preserving any indentation past it; a line below
  it ends the value.

- **Re-offer** — what happens to a line that a multiline value declines: rather
  than being discarded, it is handed back to `incorporate_node`'s ordinary
  walk-up and competes as an ordinary sibling or child, which may succeed or
  raise `OutOfContextNodeError` (§5.3, §9.3, B5).

- **Closed node** — a key-value pair or list item that already holds a child.
  It accepts nothing further, whatever the candidate's type or level, so a
  deeper following line that is not a valid continuation is always a context
  violation (§9.3).

- **Sibling column** — the column a mapping or list registers as the exact
  indentation its members must match. For a mapping opened by an inline key
  after a list marker (`-   name: Alice`), it is the key's own column, not the
  line's indentation (§6.2, M23).

- **Fallthrough** (scalar fallthrough) — the §7.6 rule that a line failing every
  structural form is taken literally as scalar text rather than guessed at, so
  `key:value` and `-item` are plain strings. The one exception is an inline
  value beginning with a quote character, which is a
  `MalformedQuotedStringError`.

- **Quoted value** — a single- or double-quoted string at an inline position
  (§4.7). It opens and closes on one line, preserves its interior whitespace,
  and is a complete value: it accepts no continuation line at all (§9.3).

- **Migration notes** — the changelog or README section listing every
  user-visible behaviour change between `syml` 0.6.2 and 1.0.0, so an upgrading
  caller can predict what will break before it does.

- **`PositionMap`** — a frozen dataclass from `src/syml/preprocess.py` holding
  the BOM offset and the normalized-text indices where a `\r\n` pair
  collapsed to `\n`. `to_original` maps a normalized `Pos` back to the
  original document; `to_original_source` does the same for a whole `Source`.
  `parse` builds one per document and threads it through `SymlParser` so
  every position reported to a caller is in original-text coordinates.

- **`EncodingError`** — a `ParseError` subclass raised when `load`'s bytes
  input fails to decode as UTF-8 (§11.3, FR-009, R-04); built by
  `encoding_error` from the originating `UnicodeDecodeError`, positioned at
  the first invalid byte.

- **`dumps`/`dump`** — `src/syml/serializer.py`'s serialization API, the
  inverse of `loads`/`load`: `dumps` renders a `str`/`list`/`dict` value to
  SYML text (raising `UnrepresentableValueError` for an unencodable value and
  `TypeError` for a non-str/list/dict), and `dump` writes that text to a file
  object in one `write()` call, writing nothing at all if `dumps` raises.

- **`Document`** — the frozen dataclass `preprocess` returns (§9.0 steps 1-3):
  `original` is the caller's untouched text, `normalized` is that text after
  BOM-stripping and CRLF/CR-to-LF normalization (the text `SymlParser` actually
  parses), and `position_map` is the `PositionMap` that translates positions
  in `normalized` back to `original`.

## Terms introduced by the language revision (spec 002)

Added by `/sp:02-specify` for `specs/002-syml-language-revision/spec.md`. The
entries above that describe comments (`comment` in the line-node rule, the
"comment lines are skipped" clauses) and quoted values predate D18 and this
revision; they are corrected when the corresponding code lands, not here.
Under the principal's ruling of 2026-09-24 the "comment lines are skipped"
clauses stay true for column-0 comments only (see **Comment** below).

- **Comment** (revised 2026-09-24) — a line whose first character, at column
  0 with no indentation, is `#`, or whose first two characters are `//`
  (FR-007, D23 as revised). It is skipped as if it were not in the document,
  anywhere: between entries, before a block's first line, and between two
  lines of an open text value, where it is neither a line of the value nor a
  paragraph break. An indented `#`/`//` line, and a `#` after a key or
  marker (`server: # prod`), is text. The grammar lexes it as the first
  alternative of `line = comment / (indent (structure / data))`, so it can
  only match at column 0; the line visitor drops it, and no node represents
  it. Not "no comments": that was the pre-ruling reading of `syml-xreq.21`.

- **Text context** — the state a block or root position enters when its first
  own line is text (FR-003). While open, every line at or past the value's
  baseline is that value's text whatever it lexes as; a line below the
  baseline closes it and is re-offered. The one piece of tree-builder state
  the revision adds back; "open text value" is the same thing.

- **Paragraph break** — an empty line inside a multi-line value, written as a
  physical blank line between two continuation lines and kept one for one
  (FR-004). A column-0 comment line between them is not counted. Blank lines before the first or after the last continuation line
  stay inert, so no value begins or ends with a paragraph break.

- **Key pattern** — `[a-z][a-z0-9_-]*` (FR-001): the whole rule for what may
  stand before a colon and be a key. Replaces D15's White_Space exclusion and
  D19's no-uppercase rule. "Would-be key" names a line that has a colon in
  key position but fails the pattern; it is text.

- **Separator whitespace** — the run of spaces or tabs between `key:` or `-`
  and an inline value (FR-008). A marker followed only by separator
  whitespace is a bare marker. Supersedes the "spaces only" reading in
  `ws`; a tab in *indentation* is still `TabIndentationError`.

- **Indentation** (revised) — a run of U+0020 only (FR-009). Every other
  White_Space code point and every control character at the start of a line
  is content, so an NBSP-only line is a text line, not a blank line.

- **Error hint** — the trailing sentence of an `OutOfContextNodeError`
  message that names the likely cause (FR-012): a would-be key on the failing
  line or the line above, or a list item at its key's column. Lives in the
  message string only; there is no reason code.

- **Coming from YAML** — the README section (FR-015) listing, in trip-over
  order, the YAML habits SYML does not share.
