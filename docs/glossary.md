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
