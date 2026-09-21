# Contract 03 — Tree building (§9.2, §9.3, §9.4, §5.3)

**Requirements**: FR-005, FR-006, FR-007 | **User stories**: US1, US4
**Spec**: §4.2, §5.1, §5.3, §6.2, §6.4, §7.3, §7.4, §8.1, §8.2, §8.3, §9.2–§9.4
**Decisions**: D11, D12, D13, D7 | **Audit gaps**: 3, 4, 5, 6, 10, 14
**`todo.txt`**: A2, A4 (reversed on class), A6, A9 (superseded by D11)

> No fenced example below carries a literal trailing space; `␠` marks one.

## Surface

```python
class SymlNode:
    level: int | None          # the node's OWN column (R-11), not the line's indent
    def can_add_node(self, node: SymlNode) -> bool: ...
    def add_node(self, node: SymlNode) -> SymlNode: ...       # returns the TIP
    def incorporate_node(self, node: SymlNode) -> SymlNode: ...
    def get_tip(self) -> SymlNode: ...


class TextLeafNode(SymlNode):
    anchor_level: int          # owning KeyValue/ListItem level; -1 for a root scalar
    baseline: int | None       # None until fixed (D11)
    quoted: bool               # a quoted inline value accepts no continuation
```

`incorporate_node` is §9.2 verbatim: accept → `add_child`; else walk to the
parent; else `OutOfContextNodeError`. `add_child` returns the **tip** of the
added subtree, which is the node the next line is tested against.

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
§9.2's walk-up. Detection happens at incorporation, before the mapping is
materialized in either data or source mode — §10.3 requires this explicitly,
because `Source` compares and hashes by text and two colliding keys would
collapse silently in a dict comprehension (see Contract 08, R-07).

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
| `empty:\nnext: value` | `{"empty": "", "next": "value"}` | | US4.1 |
| `- item1\n\n- item2\n\n\n- item3` | `["item1", "item2", "item3"]` | blanks ignored (§4.4) | §4.4 |
| `a:\n        \n  b: c\n  d: e` | `{"a": {"b": "c", "d": "e"}}` | whitespace-only line never affects indentation | US3.8 |

## Automatic container creation (§9.4)

Unchanged in shape: accepting a bare `KeyValue`/`ListItem` inserts a
`Mapping`/`List` **at the incoming node's own level**, incorporates it, then
incorporates the node into it.

## Test obligations

- Every acceptance table row and every worked case above.
- `set_level` no longer recurses into children for inline structures (R-11).
- A `DuplicateKeyError` carries `key` and `first_position` (Contract 05).
- Deep nesting at 400 levels parses; 500+ raises `RecursionError` — asserted as
  the **documented known limitation** (spec Edge Cases), not as a defect.
