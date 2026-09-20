# Glossary

Ubiquitous-language terms used across `syml`'s source and docs. The
`/glossary` skill maintains this file — it flags naming inconsistencies and
new domain concepts against the definitions below, so keep entries short and
update them here rather than letting a second name for the same concept
spread through the codebase.

- **Line node** — the result of lexing one line of SYML text in
  `src/syml/parsers.py`; every line lexes independently as
  `indent (comment / blank / structure / value)`.

- **Indentation level** — the leading-whitespace depth tagged onto each
  `SymlNode` when a line node is produced; tree building climbs and compares
  these levels to decide parent/child relationships.

- **`incorporate_node`** — the tree-building step that walks the flat list of
  line nodes and, for each one, climbs the parent chain by indentation level
  until it finds a node whose `can_add_node` accepts the newcomer.

- **`can_add_node`** — the per-node predicate a container implements to say
  whether it will accept a given child node; `incorporate_node` calls it while
  climbing the parent chain.

- **`ContainerNode`** — the base class of `Root`, `KeyValue`, and `ListItem`;
  it auto-inserts a `Mapping` or `List` intermediary when it receives a bare
  `KeyValue` or `ListItem`.

- **`TextLeafNode`** — a node that accepts further `TextLeafNode`s as
  children, which is how multiline scalar values accumulate.

- **`Source`** — a value type from `src/syml/basetypes.py` carrying filename
  plus start/end `Pos`; it compares and hashes by its text, so it works
  interchangeably with plain strings as dict keys.

- **`Pos`** — a position marker (index, line, column) used by `Source` to
  record where a value or key began and ended in the source text.

- **`OutOfContextNodeError`** — raised when no ancestor in the parent chain
  accepts an incoming node; a subclass of `ParseError` (itself a
  `ValueError`), listed in `unwrapped_exceptions` so Parsimonious does not
  wrap it.

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
