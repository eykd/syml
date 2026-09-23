# Contract 03 — Tree building (§9.2, §9.3, §9.4, §5.3)

**Requirements**: FR-005, FR-006, FR-007 | **User stories**: US1, US4
**Spec**: §4.2, §5.1, §5.3, §6.2, §6.4, §7.3, §7.4, §8.1, §8.2, §8.3, §9.2–§9.4
**Decisions**: D11, D12, D13, D7 | **Audit gaps**: 3, 4, 5, 6, 10, 14
**`todo.txt`**: A2, A4 (reversed on class), A6, A9 (superseded by D11)

> No fenced example below carries a literal trailing space; `␠` marks one.

## Surface

```python
class SymlNode:
    pnode: PNode | None        # None only on Root (§ Automatic container creation)
    source: Source             # constructor field, built by the visitor (Contract 08)
    level: int                 # the node's OWN column (R-11); required, set by the
                               # visit_* that builds it (Contract 02 § Who sets level)
    def can_add_node(self, node: SymlNode, doc: Document) -> bool: ...
    def add_node(self, node: SymlNode) -> SymlNode: ...       # returns the TIP
    def incorporate_node(self, node: SymlNode, doc: Document) -> SymlNode: ...
    def get_tip(self) -> SymlNode: ...


class TextLeafNode(SymlNode):
    inline: bool = False       # set True by visit_key_value / visit_list_item
    quoted: bool = False       # set True by visit_quoted_value (implies inline)
    anchor_level: int = -1     # set on attach (below); the default IS the root-scalar value
    baseline: int | None = 0   # set on attach; None = inline, not yet fixed (D11)
```

### Where `anchor_level` and `baseline` are assigned (red-team pass 11)

The visitor cannot set them for a bare line: `visit_text` does not know
whether its line will become a root scalar, a block value, or a continuation
candidate. The visitor knows only `inline` / `quoted`, so it sets those; the
**accepting node** sets the rest when it attaches the leaf:

```python
class ContainerNode(SymlNode):                  # KeyValue, ListItem
    def add_node(self, node: SymlNode) -> SymlNode:
        self.children.append(node)
        node.parent = self
        if isinstance(node, TextLeafNode):
            node.anchor_level = self.level
            node.baseline = None if node.inline else node.level   # inline vs block (§9.3)
        return node.get_tip()


class Root(ContainerNode):
    def add_node(self, node: SymlNode) -> SymlNode:
        self.children.append(node)
        node.parent = self
        # a root scalar keeps the defaults: anchor_level -1, baseline 0 (§9.3)
        return node.get_tip()


class TextLeafNode(SymlNode):
    def add_node(self, node: SymlNode) -> SymlNode:        # a continuation line
        if self.baseline is None:
            self.baseline = node.level                     # first continuation fixes it
        self.children.append(node)
        node.parent = self
        return self                                        # tip unchanged (§9.3)

    def get_tip(self) -> SymlNode:
        return self                                        # continuations are never tips
```

`Root` never receives an inline leaf: inline leaves are attached inside
`visit_key_value` / `visit_list_item`, before the line's top node reaches the
per-line loop. `ParentNode` (`Mapping`, `List`) never accepts a
`TextLeafNode`. A continuation child's own `anchor_level` / `baseline` are never
read, because it is never a tip; `as_data` reads only its `level` and text
(`' ' * (child.level - self.baseline) + text`). `baseline` is always an `int`
by the time a continuation child exists, so that subtraction never sees
`None`.

`incorporate_node` is §9.2 verbatim: accept → `add_child`; else walk to the
parent; else `OutOfContextNodeError`. `add_child` returns the **tip** of the
added subtree, which is the node the next line is tested against.

**Signature change from today: `doc: Document` is now a required second
argument.** Today's `fail_to_incorporate_node` builds its position and
`line_text` from `pnode.full_text` alone (`Pos.from_str_index` +
`utils.get_line`), which only works because `pnode.full_text` is the whole
document under `document.parse(text)`. Per-line lexing (Contract 02) makes
`pnode.full_text` a single **line**, so that derivation is gone. The
replacement reads `position` off the node's own `Source` (already in original
coordinates — Contract 08) and calls Contract 05's `original_line(doc,
position.line)` for `line_text`, so `doc` must be in scope wherever a
`ParseError` can be raised:

```python
def fail_to_incorporate_node(self, node: SymlNode, doc: Document) -> NoReturn:
    """Contract 05's OutOfContextNodeError, anchored at the offending node's
    own Source.start (already original coordinates; no re-derivation)."""
    position = node.source.start
    raise OutOfContextNodeError(
        'Failed to incorporate a node', position, original_line(doc, position.line),
    )
```

Every recursive `incorporate_node` call (walking to the parent, or into an
auto-created `Mapping`/`List` intermediary) forwards the same `doc` unchanged;
it is never re-derived or defaulted. `can_add_node` gains the same second
argument for the one caller that needs it (`Mapping`'s duplicate-key check,
below); every other override ignores it. Contract 02's per-line loop calls
`tip = tip.incorporate_node(node, doc)` — the `doc` it already built from
`preprocess(text, filename)` — replacing the earlier, undefined two-argument
`incorporate(tip, node)`.

An inline structural value (`- key: v`, `- - x`) goes through the **same**
algorithm, not a direct attach (§9.2). That is already true today and must stay.

## Acceptance table (§9.3)

| Current | Accepts | Condition | Delta from today |
| --- | --- | --- | --- |
| `Root` | any | empty and `node.level >= 0` | — |
| `List` | `ListItem` only | `node.level == self.level` | **`>=` → `==`** (audit gap #3) |
| `ListItem` | any | empty and `node.level > self.level` | closed-node rule now enforced |
| `Mapping` | `KeyValue` only | `node.level == self.level`; duplicate key → raise | **`>=` → `==`**; duplicate check is new |
| `KeyValue` | any | empty and `node.level > self.level` | closed-node rule now enforced |
| `TextLeafNode` | `TextLeafNode` only | baseline condition below | **level was ignored entirely** (audit gap #4) |

**Closed-node rule (§9.3)**: a `KeyValue` or `ListItem` holding any child returns
`False` unconditionally, whatever the candidate's type or level.

**No partial matching (§9.3)**: a level matching nothing on any ancestor up to
`Root` raises `OutOfContextNodeError`. `==` on `List`/`Mapping` is also §6.4's
homogeneity enforcement.

## TextLeafNode continuation (§5.3, D11)

| Origin | `anchor_level` | baseline fixed | fixed to |
| --- | --- | --- | --- |
| inline (`key: a`) | owner's level | on first accepted continuation | that candidate's own level |
| block (first block line) | owner's level | at creation | the block line's level |
| root scalar | `-1` | at creation | `0`, unconditionally |
| quoted inline | owner's level | never | accepts nothing |

Before the baseline is fixed (inline only), a candidate must have
`level > anchor_level` (§5.1 rule 1). Once fixed, a candidate is accepted iff
`level >= baseline`.

**Indentation preservation**: an accepted continuation at level `L` contributes
`' ' * (L - baseline) + text`.

**Re-offer (B5)**: a declined candidate is not discarded — §9.2's walk-up
re-offers it to the owning container, where it may succeed or raise.

**Skipping (D12)**: blank and comment lines inside a value are discarded at any
indentation; they neither add a line nor end the value nor affect the baseline.

**Lexing precedence (D13)**: a candidate that lexed as structure is never
offered to `TextLeafNode.can_add_node`; `TextLeafNode` only ever accepts another
`TextLeafNode`.

## Duplicate keys (FR-007, §8.3, §10.3)

`Mapping.can_add_node` compares the incoming key to its existing children's keys
by **code point** (case-sensitive, no Unicode normalization). On a match it
raises `DuplicateKeyError` **immediately** and does **not** fall through to
§9.2's walk-up:

```python
def can_add_node(self, node: SymlNode, doc: Document) -> bool:
    if not (isinstance(node, KeyValue) and node.level == self.level):
        return False                                          # walk up; NO duplicate check
    for child in self.children:
        if child.key.as_data() == node.key.as_data():         # code-point compare
            position = node.source.start
            raise DuplicateKeyError(
                'Duplicate key', position, original_line(doc, position.line),
                key=node.key.as_data(), first_position=child.source.start,
            )
    return True
```

**The level gate comes first.** §9.3's table scopes the duplicate check to
`new_node.level == mapping.level`. Scanning before the level test would
reject valid documents: for `p:\n  a: 1\na: 2`, the walk-up from `a: 2`
offers it to the level-2 `Mapping` holding `a` *before* it reaches the root
mapping. That mapping must decline on level alone and let the walk continue
(§8.3: "the same key may appear in different nested mappings").

`KeyValue.key` is a `KeyLeafNode` (data-model.md §3), not a string; `.as_data()`
is the existing `str` conversion `Mapping.as_data`/`as_source` already use
(`c.key.as_data()` / `c.key.as_source()`), reused here so the comparison and
the `DuplicateKeyError.key: str` attribute agree on the same text.

Detection happens at incorporation, before the mapping is materialized in
either data or source mode — §10.3 requires this explicitly, because `Source`
compares and hashes by text and two colliding keys would collapse silently in
a dict comprehension (see Contract 08, R-07). `doc` is the same `Document`
`incorporate_node` was called with, passed through unchanged.

A level mismatch (`node.level != mapping.level`) performs **no** duplicate check
and walks up normally.

## Absent values (FR-005)

| Situation | Result | Was |
| --- | --- | --- |
| `key:` with no child | `""` | `None` |
| `key:␠` with no child | `""` (D6) | `IncompleteParseError` |
| empty document | `""` | `None` |
| comment-only document | `""` | `None` |
| `-` with no child | `""` | — |

`ContainerNode.as_data` / `as_source` return `''` / an empty `Source` instead of
`None` when childless. **Invariant**: no `loads`/`load` result contains `None`
at any depth (US4 scenario 5).

## Worked cases

Each row is an acceptance scenario. `→` is `loads`.

| Input | Result | Why | Scenario |
| --- | --- | --- | --- |
| `parent:\n  child1: value\n child2: value` | `OutOfContextNodeError` | 3 ≠ 2 and 3 ≯ nothing | US1.1 |
| `note: hello\n  more: text` | `OutOfContextNodeError` | `note` closed by its inline value | US1.2 |
| `key:\n  first\n    indented\n  back` | `{"key": "first\n  indented\nback"}` | baseline 2; 4 preserves +2 | US1.3 |
| `key: a\nb` | `OutOfContextNodeError` | `b` at 0 is not `> anchor_level` 0 | US1.4 |
| `key: a\n    b\n  c` | `OutOfContextNodeError` | `b` fixes baseline 4; `c` at 2 terminates, re-offers, finds nothing | US1.5 |
| `hello\n  world\nagain` | `"hello\n  world\nagain"` | root scalar baseline 0 | US1.6 |
| `a:\n  b: 1\n  plain` | `OutOfContextNodeError` | plain text at a container's own level (M24) | US1.7 |
| `-   name: Alice\n  role: admin` | `OutOfContextNodeError` | `name`'s column is 4 (M23) | US1.8 |
| `key: value1\nkey: value2` | `DuplicateKeyError` | at incorporation | US1.9 |
| `a: Note\n  Big Warning: do not touch` | `{"a": "Note\nBig Warning: do not touch"}` | `Big Warning` is not a key | US1.10 |
| `a: Note\n  Warning: do not touch` | `OutOfContextNodeError` | `Warning` **is** a key; `a` is closed (D13) | §7.6 |
| `p:\n  a: 1\n  a: 2` | `DuplicateKeyError` | per-mapping, nested too | Edge Cases |
| `p:\n  a: 1\na: 2` | `{"p": {"a": "1"}, "a": "2"}` | the inner mapping declines on level **before** any duplicate scan (§9.3) | §8.3 |
| `empty:\nnext: value` | `{"empty": "", "next": "value"}` | | US4.1 |
| `key:␠\n  nested: content` | `{"key": {"nested": "content"}}` | empty unquoted inline `text` dropped by the visitor; `key` stays open (D6, Contract 02) | US3.7 |
| `-␠\n  x` | `["x"]` | same normalization for a list item (D6) | §9.3 |
| `key: ""\n  x: y` | `OutOfContextNodeError` | a quoted empty value is a real child and closes `key` (§9.3, §4.7) | §9.3 |
| `- item1\n\n- item2\n\n\n- item3` | `["item1", "item2", "item3"]` | blanks ignored (§4.4) | §4.4 |
| `a:\n        \n  b: c\n  d: e` | `{"a": {"b": "c", "d": "e"}}` | whitespace-only line never affects indentation | US3.8 |

## Automatic container creation (§9.4)

Unchanged in shape: accepting a bare `KeyValue`/`ListItem` inserts a
`Mapping`/`List` **at the incoming node's own level**, incorporates it, then
incorporates the node into it.

**Construction changed, though.** Today every node computes its `source` in
`__post_init__` as `Source.from_node(pnode, filename)`. Contract 08's
`from_node` now needs `(pnode, line, position_map, filename)`, and neither
`incorporate_node` (which has `doc` but no `line`) nor the per-line loop's
`Root` (which has no document-level `pnode` at all) can supply that. So:

- `source: Source` becomes an ordinary **constructor field** on `SymlNode`,
  not something `__post_init__` derives. The visitor builds it with
  `Source.from_node(pnode, self.line, self.doc.position_map, self.doc.filename)`
  (Contract 08) and passes it in.
- An intermediary copies the triggering node's `Source`:
  `Mapping(pnode=node.pnode, source=node.source, level=node.level)` (and the
  same for `List`). No `line` is needed.
- `pnode` becomes `PNode | None`, and it is `None` only on `Root`.
  `Root(pnode=None, source=Source(filename=doc.filename, start=Pos(0, 1, 0),
  end=Pos(0, 1, 0), text=''))` is the "`Source` over the empty span" that
  data-model §3.5 promises for an empty or comment-only document. Contract
  02's loop constructs it.

## Test obligations

- Every acceptance table row and every worked case above.
- `set_level` is gone (R-11): no node's `level` is `None` or changed after
  construction; `-   name: Alice` gives `ListItem`/`Mapping`/`KeyValue`/leaf
  levels 0/4/4/10 (Contract 02 § Who sets `level`).
- `anchor_level`/`baseline` per origin: `key: a` → anchor 0, baseline `None`
  until `  b` fixes it to 2; `key:\n  a` → anchor 0, baseline 2 at attach;
  `hello` (root) → anchor -1, baseline 0; after a continuation the tip is still
  the first leaf, never the continuation child.
- A `DuplicateKeyError` carries `key` and `first_position` (Contract 05).
- A dedented key equal to a key in a deeper mapping on the walk-up path
  (`p:\n  a: 1\na: 2`) is **not** a duplicate. This pins the level-gate
  ordering in `Mapping.can_add_node`.
- A comment line inside a value, and a comment-only document, never reach
  `incorporate_node`. `"key: a\n  # c\n  b"` gives `{"key": "a\nb"}`, and
  `"# only"` gives `""` (Contract 02's comment branch; `Comment` is a
  `TextLeafNode` subclass, so an unrouted comment would join as continuation
  text).
- `parse("").as_source()` is an empty `Source` at `Pos(0, 1, 0)` for both
  endpoints, carrying `filename`. An auto-created `Mapping`/`List` carries
  the `Source` of the node that triggered it.
- `OutOfContextNodeError.line_text` and `DuplicateKeyError.line_text` are the
  original line (BOM/CRLF-bearing inputs included), not the normalized one —
  asserting the `doc`-threading above actually reaches both raise sites.
- Deep nesting at 400 levels parses; 500+ raises `RecursionError` — asserted as
  the **documented known limitation** (spec Edge Cases), not as a defect.
- Inline nesting on one line: `'- ' * 50 + 'x'` parses (the lexing threshold
  is 123 at the default limit with no test-harness frames on the stack); `'- ' * 200 + 'x'`
  raises the host `RecursionError` (not `VisitationError`) at the default
  recursion limit — the same known limitation, at a much lower depth, because
  the recursion is in lexing (Contract 05).
