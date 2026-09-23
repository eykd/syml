# Phase 1 Data Model: syml 1.0 Spec Conformance

**Feature**: `001-syml-1-0-conformance` | **Date**: 2026-09-21
**Derives from**: `spec.md` § "Key Entities", `SYML-SPECIFICATION.md` §9–§11,
`research.md` R-01..R-11.

> Fenced examples below never carry a literal trailing space — the repository's
> `trailing-whitespace` pre-commit hook strips them. Where a trailing space is
> significant it is written `␠` (U+2420 SYMBOL FOR SPACE). See research.md R-05.

---

## 1. Document

The caller's text in two forms. Every parsing rule operates on the normalized
form; every position reported to a caller refers to the original.

| Field | Type | Notes |
| --- | --- | --- |
| `original` | `str` | exactly what the caller passed to `loads`, or what `load` decoded |
| `normalized` | `str` | after §9.0 steps 1–2 |
| `position_map` | `PositionMap` | normalized index → original index (R-02) |
| `filename` | `StrPath \| None` | carried into every `Source` and every `ParseError` message |

**Invariants**

- `normalized` contains no `\r` and no leading U+FEFF at index 0.
- `normalized.count('\n') == ` the number of line breaks in `original`,
  counting `\r\n` as one.
- A second U+FEFF immediately after a stripped one is ordinary content and
  survives into `normalized` (spec Edge Cases).
- `original == ''` and `original == '\ufeff'` both normalize to `''`, which is
  the empty document (§7.4) and yields `""`.

### 1a. PositionMap

| Field | Type | Notes |
| --- | --- | --- |
| `bom_offset` | `int` | 0 or 1 |
| `crlf_indices` | `tuple[int, ...]` | sorted normalized indices where a `\r\n` collapsed (a tuple: `PositionMap` is frozen) |

`to_original(p: Pos) -> Pos`:

- `index` → `p.index + bom_offset + bisect_left(crlf_indices, p.index)`
- `line` → unchanged
- `column` → `p.column + bom_offset` when `p.line == 1`, else unchanged

**Invariants**: `to_original` is monotonically non-decreasing in `index`;
`bisect_left` is used (not `bisect_right`) so a position *at* a collapsed break —
an exclusive `end` at a CRLF line end, or an empty token at end of line — maps
to the `\r`, keeping `index` consistent with `line`/`column` and making
`original[start.index:end.index]` exactly the token's original text (Contract 01).

---

## 2. Line

One physical line of `normalized`, terminated by a single U+000A. Produced by
splitting on `\n` **only** — never `str.splitlines()` (§13.3, audit gap #16).
A `NamedTuple` in `basetypes.py`, beside `Pos` and `pos_at`, so
`Source.from_node` never imports `preprocess` at run time (Contract 01,
red-team pass 17).

| Field | Type | Notes |
| --- | --- | --- |
| `text` | `str` | the line without its terminator |
| `start` | `int` | index of the line's first character in `normalized` |
| `number` | `int` | 1-indexed (§10.2) |

Each line classifies, independently of its neighbours (§5.1 rule 6), into
exactly one of:

| Kind | Recognized when | Effect on the tree |
| --- | --- | --- |
| **blank** | leading-whitespace run is the whole line (`preprocess.is_blank`: only U+0020/U+0009, any mixture) | skipped entirely — dropped by the per-line loop **before lexing** (Contract 02), because a tab-bearing blank would otherwise lex as non-empty `data`; never incorporated, never affects a baseline or an indentation level (§4.4, D12, D14, audit gap #13) |
| **comment** | first non-indent characters are `#` or `//` | skipped; attached to `comments` on the current tip |
| **structure** | matches `list_item` / `key_value` / `section` | incorporated as a node |
| **scalar text** | everything else (`data`) | incorporated as a `TextLeafNode` |

**State transition (pre-processing, §9.0 step 3)**: blank is decided **before**
the tab scan. A line of only spaces and a tab is blank and raises nothing
(US2 scenario 6, D14).

---

## 3. Node tree

```
SymlNode
├── ContainerNode        # holds at most one value; "closed" once it does
│   ├── Root             # level 0
│   ├── KeyValue         # + key: KeyLeafNode
│   └── ListItem
├── ParentNode           # holds many same-level children
│   ├── Mapping
│   └── List
├── TextLeafNode         # + inline, quoted, anchor_level, baseline
│   └── Comment
└── KeyLeafNode
```

### 3.1 Fields added or changed by this feature

| Node | Field | Type | Why |
| --- | --- | --- | --- |
| `SymlNode` | `level` | `int` | **semantics change**: the node's *own* column, not the line's indent (R-11, §9's Level definition, M23). **Required** at construction, set by the building `visit_*` from its own line-local `pnode.start`; never `None`, never reassigned — `set_level` is deleted (Contract 02 § Who sets `level`) |
| `TextLeafNode` | `inline` | `bool` | `True` when built at an inline position; set by `visit_key_value`/`visit_list_item` for an unquoted leaf, and at construction by `visit_quoted_value` for a quoted one (Contract 05). Decides, at attach time, whether the baseline starts unset (inline) or fixed (block) |
| `TextLeafNode` | `anchor_level` | `int` | level of the owning `KeyValue`/`ListItem`; `-1` for a root scalar (§9.3). Assigned by the accepting node's `add_node`, not the visitor (Contract 03 § Where `anchor_level` and `baseline` are assigned); default `-1` |
| `TextLeafNode` | `baseline` | `int \| None` | `None` until fixed; see 3.3 (D11). Assigned on attach (`None` if `inline`, else the leaf's own level; `0` for a root scalar), fixed by the first continuation for inline |
| `TextLeafNode` | `quoted` | `bool` | a quoted inline value accepts no continuation (§9.3, D2); set by `visit_quoted_value` |
| `ContainerNode` | — | — | "closed" is derived: `bool(self.children)` |
| `Mapping` | `keys` | `dict[str, KeyValue]` | key text → the first `KeyValue` holding it, filled by `Mapping.add_node`; makes the duplicate-key check at `can_add_node` time (FR-007, §10.3) a lookup instead of an O(*n*) scan per key (Contract 03, red-team pass 16) |

### 3.2 Acceptance rules (§9.3), as the implementation must encode them

| Current node | Accepts | Condition |
| --- | --- | --- |
| `Root` | any | empty **and** `node.level >= 0` |
| `List` | `ListItem` only | `node.level == self.level` (**`==`**, not `>=` — audit gap #3) |
| `ListItem` | any | empty **and** `node.level > self.level` |
| `Mapping` | `KeyValue` only | `node.level == self.level`; if the key is already present → raise `DuplicateKeyError` **immediately**, do **not** walk up |
| `KeyValue` | any | empty **and** `node.level > self.level` |
| `TextLeafNode` | `TextLeafNode` only | see 3.3 |

**Closed-node rule**: a `KeyValue` or `ListItem` with any child returns `False`
unconditionally, whatever the candidate's type or level (§9.3). This is what
makes `note: hello` + `  more: text` an error (US1 scenario 2).

**No partial matching anywhere**: a level that fits no relationship on any
ancestor up to `Root` is `OutOfContextNodeError`. This is also §6.4's
homogeneity enforcement — a `List` never accepts a `KeyValue`, a `Mapping` never
accepts a `ListItem` — so mixing structure types at one level always fails all
the way up.

### 3.3 TextLeafNode state machine (§5.3, D11)

```
                     ┌──────────────────────────┐
  inline value  ───► │ baseline = None          │
                     │ (anchor_level known)     │
                     └─────────┬────────────────┘
                               │ first candidate with level > anchor_level
                               ▼
  block value   ───► ┌──────────────────────────┐
  (baseline =        │ baseline = <fixed int>   │ ◄── accepts candidate
   own first-line    │                          │     iff level >= baseline;
   level)            └──────────────────────────┘     text appended, tip unchanged
  root scalar   ───►   baseline = 0 (always)

  quoted inline ───► ┌──────────────────────────┐
                     │ accepts nothing, ever    │
                     └──────────────────────────┘
```

| Origin | `anchor_level` | `baseline` fixed | Fixed to |
| --- | --- | --- | --- |
| inline after `key:`/`- ` | owning node's level | on first accepted continuation | that candidate's own level |
| block value (first block line) | owning node's level | at creation | the block line's own level |
| root scalar | `-1` | at creation | `0`, unconditionally |
| quoted inline | owning node's level | n/a | never accepts |

**Indentation preservation**: an accepted continuation at level `L` contributes
`' ' * (L - baseline) + text` to the joined value. The head line gets the same
prefix, `' ' * (level - baseline)`, unless it is inline — non-zero only for a
root scalar, so `  hello\nworld` is `"  hello\nworld"` (§5.3; Contract 03
§ Root-scalar head indentation). This is the change behind
US1 scenario 3 (`key:` / `  first` / `    indented` / `  back` →
`"first\n  indented\nback"`) and audit gap #4.

**Re-offer (B5)**: a candidate the `TextLeafNode` declines is **not** discarded.
§9.2's ordinary walk-up re-offers it to the owning container, where it competes
as a sibling or child and may succeed (a dedented sibling key) or raise
(US1 scenarios 4, 5).

**Lexing precedence**: a candidate that lexed as `list_item`/`key_value`/
`section` is a different node type and is never offered to `TextLeafNode.can_add_node`
at all (D13). This is why `a: Note` / `  Warning: do not touch` raises while
`a: Note` / `  Big Warning: do not touch` joins as prose (US1 scenario 10).

### 3.4 Automatic container creation (§9.4)

Unchanged in shape from today's `ContainerNode.incorporate_node`: on accepting a
bare `KeyValue` or `ListItem`, insert a `Mapping` or `List` at the **incoming
node's** level, incorporate it, then incorporate the node into it. The level it
registers is the node's own column (R-11), which is what makes
`-   name: Alice` register column 4 rather than column 0.

`source` is a constructor field, no longer derived in `__post_init__`.
Contract 08's `Source.from_node` needs a `line` that `incorporate_node` does
not have. An intermediary therefore copies the triggering node's `Source`.
`Root` has `pnode=None` and an empty `Source` at `Pos(0, 1, 0)` (Contract 03).

### 3.5 Rendering

| Method | Leaves are | Absent value yields |
| --- | --- | --- |
| `as_data()` | `str` | `""` (**changed** — was `None`; FR-005) |
| `as_source()` | `Source` | zero-width `Source` at the container's own `source.end` (Contract 03 § Absent values) |

**Invariant (FR-005, SC measured by US4 scenario 5)**: no result of `loads` or
`load` contains `None` at any depth.

---

## 4. Source and Pos

| `Pos` field | Type | Semantics |
| --- | --- | --- |
| `index` | `int` | 0-indexed code-point offset **into the original text** (FR-013) |
| `line` | `int` | 1-indexed (§10.2) |
| `column` | `int` | 0-indexed code-point column |

| `Source` field | Type | Semantics |
| --- | --- | --- |
| `filename` | `StrPath \| None` | |
| `start`, `end` | `Pos` | original-text coordinates, built by `Source.from_node(pnode, line, position_map, filename)` as `to_original(pos_at(line, offset))` — `pnode` offsets are line-local under per-line lexing (Contract 08) |
| `text` | `str` | the decoded value — quoted values carry the **decoded** text, not the raw source slice; their `start`/`end` span the raw token from the opening quote to just past the closing quote, exclusive (Contract 08) |

**Equality/hash**: by `text` only (R-07, §10.3), against a `str` or another
`Source`; any other operand is `NotImplemented`, so `Source('1') == 1` is
`False` (red-team pass 20, Contract 08). Equality never compares positions,
so tests assert `start`/`end` field by field. The `# pragma: no cover` on
`__hash__` is removed and it is tested. The dead `return self + other.text`
in `__add__` is deleted (`todo.txt` B3, FR-017), its `str` branch counts the
joining `\n`, and no parse path calls `__add__`.

**`from_str_index`/`from_text` line counting**: `Pos.from_str_index` and
`Source.from_text` — kept for tests, never used for parse positions — count
only `\n` as a line break, so U+2028 and U+0085 no longer start a line
(red-team pass 23, Contract 08).

**Continuation spans**: when a `TextLeafNode` absorbs a continuation line, the
resulting `Source.start` stays at the value's first character (for a root scalar
whose first line is indented, the first preserved indent space — Contract 03)
and `end` moves to the last accepted character; `text` equals what `as_data()` returns for the same
node (including preserved indentation), so `str(source) == node.as_data()` holds.
`TextLeafNode.as_source()` builds that `Source` directly, taking `text` from
`as_data()` (Contract 03, red-team pass 20).

---

## 5. Error hierarchy

```
ValueError
├── ParseError                       (message, position: Pos, line_text: str)
│   ├── OutOfContextNodeError
│   ├── DuplicateKeyError            + key: str, first_position: Pos   (also in .args)
│   ├── TabIndentationError
│   ├── MalformedQuotedStringError   + escape: str | None, code_point: int | None   (also in .args)
│   └── EncodingError                (new; §11.3 amended — FR-009, R-04)
└── UnrepresentableValueError        (raised by dumps, not loads)
```

Seven exported classes. `DocumentLimitError` is **not** among them (spec Edge
Cases; §11.3 and §13.4 are edited to mark limits post-1.0).

Attribute contract and per-class position anchors: see `contracts/05-errors.md`.
The extra attributes are appended to `.args` (`e.args[:3]` is always
`(message, position, line_text)`), so every class survives `pickle` and
`copy.copy`, which rebuild an exception as `cls(*e.args)` (red-team pass 18).

---

## 6. Validation rules traced to requirements

| Rule | Entity | Requirement | Spec |
| --- | --- | --- | --- |
| exactly one leading BOM stripped | Document | FR-002 | §9.0.1, §13.3 |
| CRLF and bare CR → LF | Document | FR-002 | §9.0.2, §4.8 |
| tab in a non-blank line's leading whitespace → `TabIndentationError` | Line | FR-002 | §9.0.3, §8.4, D14 |
| blank decided before the tab scan | Line | FR-002 | §9.0.3, §4.4, D14 |
| split on `\n` only | Line | FR-003 | §13.3 |
| key excludes `White_Space` ∪ C0 ∪ C1 | KeyLeafNode | FR-004 | §4.5, D15, R-01 |
| `key:value`, `-item` fall through to scalar | Line | FR-004 | §7.6 |
| `key:␠` ≡ `key:` | Line | FR-004 | D6, §9.3 |
| absent value → `""` | rendering | FR-005 | §7.3, §7.4, §11.1 |
| siblings match on `==` | List, Mapping | FR-006 | §9.3, B4 |
| closed node accepts nothing | KeyValue, ListItem | FR-006 | §9.3 |
| baseline per D11; preserve beyond it | TextLeafNode | FR-006 | §5.3, D11 |
| below-baseline terminates and re-offers | TextLeafNode | FR-006 | §5.3, B5 |
| plain text at a container's level errors | Mapping, List | FR-006 | §6.4, M24 |
| inline key after `-` sets the sibling column | Mapping | FR-006 | §6.2, M23 |
| duplicate key → error at incorporation | Mapping | FR-007 | §8.3, §10.3 |
| quoting only at an inline position | Line | FR-008 | §4.7, D2 |
| quoted value accepts no continuation | TextLeafNode | FR-008 | §9.3, §4.1 |
| seven error classes, named attributes | Error hierarchy | FR-009 | §11.3 |
| binary `load` → strict UTF-8 or `EncodingError` | Document | FR-010 | §11.1 |
| `loads(dumps(x)) == x` | serializer | FR-011 | §11.2.1 |
| positions in original text | Pos | FR-013 | §10.1–10.2 |
