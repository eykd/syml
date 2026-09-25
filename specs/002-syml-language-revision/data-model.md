# Data Model: SYML Language Revision — Values Are Just Text

**Feature**: `002-syml-language-revision` | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

The public data model does not change: `loads` still returns `SymlData`
(`str | list[SymlData] | dict[str, SymlData]`), every leaf is a plain `str`,
and `dumps` still takes `SymlInput`. What changes is the internal node tree
that `parse()` builds, the language entities the spec defines, and the
exception surface. Entities below follow the spec's Key Entities list.

---

## Language entities

| Entity | Status | Definition after this feature | Source |
| --- | --- | --- | --- |
| **Indentation** | revised | The run of U+0020 at the start of a line (`indent = ~" *"`). Nothing else is indentation. A line's level is the length of that run. | FR-009, D14 affirmed |
| **Blank line** | revised | A line consisting only of U+0020 and U+0009 (or empty). Classified by the line visitor, not a grammar rule. A NBSP-only line is **not** blank. | §4.4, §9.0 step 3, FR-009 |
| **Key** | revised | Exactly `[a-z][a-z0-9_-]*`, preceded by nothing but indentation, followed by `:`. The whole rule; no out-of-PEG check. | FR-001, D20 |
| **Separator whitespace** | revised | `ws = ~"[ \t]+"`: the run of spaces or tabs after `key:` or `-`. A marker followed only by separator whitespace is bare (D6). | FR-008, D24 |
| **Text context** | new | The state a value is in once its first own line is text. While the value's `TextLeafNode` is the tip, every non-blank line at or past its threshold (baseline, or `> anchor_level` before a baseline exists) is that value's text, whatever it lexes as. A line below the threshold closes it and is re-offered (§5.3). | FR-003, D21 |
| **Paragraph break** | new | An empty line inside a multi-line value, one per physical blank line between two lines of the same value (an inline value's text counts as its first line, R-04). | FR-004, D22 |
| **Comment** | removed | No line is a comment. `#` and `//` are text everywhere. | FR-007, D23 |
| **Strict child depth** | revised | Every child is strictly deeper than its parent, list items included; the indentless-sequence carve-out is gone. `- key:`'s sibling-column rule (§6.2) is unchanged. | FR-010, D25 |
| **Error hint** | new | An optional trailing sentence of an out-of-context message: would-be key, or list at its key's column. | FR-012 |
| **Unrepresentable set** | shrunk | research.md R-05's eight items. | FR-006, FR-002 |

---

## Parse-tree nodes (`src/syml/nodes.py`)

### `SymlNode` (base)

| Field | Change | Notes |
| --- | --- | --- |
| `pnode` | unchanged | The node's own parse node. |
| `level` | unchanged | The node's own column (R-11 of 001). |
| `parent`, `children`, `filename`, `position_map`, `source` | unchanged | |
| `comments` | **removed** | FR-007. |
| `content_pnode: PNode \| None = None` | **new**, `repr=False` | Set by `visit_line` on the node a physical line lexes to: the parse node spanning the line's content after the indentation. Used only by `TextLeafNode.incorporate_node` to re-read a structure-shaped line as text (R-01). `None` on inline sub-nodes. |
| `line_pnode: PNode \| None = None` | **new**, `repr=False` | Set by `visit_line`: the parse node of the whole line including indentation. Used only by `Root` to build a root scalar's first line with its indentation (R-12). |

`fail_to_incorporate_node` moves its message construction to `Root` (the only
node that reaches it, since the walk-up always ends at `Root`): it reads the
open columns off the rightmost spine and the line above from `full_text`
(R-08), and raises `OutOfContextNodeError(description, pos, line_text, filename=...)`.

### Removed classes

- **`IndentNode`**: the line visitor reads the indentation width directly;
  nothing consumes the node.
- **`Comment`**: FR-007.

### `ContainerNode` / `KeyValue` / `ListItem` / `Root`

| Node | Acceptance rule after this feature | Change |
| --- | --- | --- |
| `ContainerNode` | empty and `node.level > self.level` | unchanged |
| `KeyValue` | as `ContainerNode` for every node type | **The `ListItem \| List` carve-out (`>=`) is deleted** (FR-010). |
| `ListItem` | as `ContainerNode` | unchanged |
| `Root` | empty and `node.level >= 0` | unchanged rule; **new** `incorporate_node` override: when empty and offered a plain `TextLeafNode` from a physical line, rebuild it over `line_pnode` (column 0, indentation included) before accepting; `add_node` fixes that leaf's baseline at 0 (FR-005, R-12). **New** `fail_to_incorporate_node` override builds the FR-012 message. |
| `List` | `node.level == self.level` and `ListItem` | unchanged |
| `Mapping` | `node.level == self.level` and `KeyValue`; duplicate → `DuplicateKeyError` | raises with `filename=` instead of a hand-built prefix (R-07) |

### `TextLeafNode`

| Field / method | Change | Notes |
| --- | --- | --- |
| `inline`, `anchor_level`, `baseline` | unchanged | D11 still governs the baseline. |
| `blank_lines_before: int = 0` | **new** | Set by the parent value's `add_node` from the normalized-text gap (R-03). Meaningful only on continuation children. |
| `accepts_level(level) -> bool` | **new** | Factored out of `can_add_node`: `level > anchor_level` while `baseline is None`, else `level >= baseline`. `None` level → `False`. |
| `can_add_node(node)` | refactored | `isinstance(node, TextLeafNode) and self.accepts_level(node.level)`. |
| `incorporate_node(node)` | **new override** | If `node` is not a `TextLeafNode`, has a `content_pnode`, and `accepts_level(node.level)`, replace it with `TextLeafNode(pnode=node.content_pnode, ...)`; then defer to `SymlNode.incorporate_node` (R-01). |
| `add_node(node)` | extended | Also computes `node.blank_lines_before`. |
| `as_data()` | extended | Emits `blank_lines_before` empty strings before each continuation. |
| `as_source()` | unchanged shape | `text` mirrors `as_data()` (paragraph breaks included); `start` is the first line's first character (column 0 for a root scalar, R-12); `end` is the last continuation's end. |

State transitions of a value (per text leaf):

```text
            first own line is text
 (empty) ─────────────────────────────▶ OPEN(baseline fixed | unset for inline)
                                           │  line ≥ threshold (any shape) → append (+ blank_lines_before)
                                           │  blank line                  → skipped (counted later)
                                           ▼
                                  line < threshold → CLOSED; line re-offered up the tree
```

### `KeyLeafNode`

Unchanged. Its text is always `[a-z][a-z0-9_-]*`.

---

## Parser (`src/syml/parsers.py`)

| Element | Change |
| --- | --- |
| `SymlParser.grammar` | Replaced by research.md R-02's rule set (Contract 01). |
| `visit_line` | Returns `None` for a blank content span; otherwise returns the lexed node with `content_pnode`/`line_pnode` set. |
| `visit_document` | Replaces `visit_lines`: flattens the visited children and incorporates each line into the tip, starting at a new `Root`. |
| `visit_key_value`, `visit_section` | Lose the D19 text fallthrough. |
| `visit_key_colon` | Renamed from `visit_section` (rule rename). |
| `visit_blank`, `visit_comment`, `visit_indent`, `key_has_uppercase`, `_is_text_line`, `_text_leaf` | Removed. |

---

## Pre-processing (`src/syml/preprocess.py`)

| Element | Change |
| --- | --- |
| `preprocess(text, filename)` | Builds the `PositionMap` before the tab scan and passes it, with `filename`, into the scan. |
| `_scan_for_tab_indentation(normalized, position_map, filename)` | Maps its `Pos` through `PositionMap.map`; raises with `filename=` (R-09). The scanned run is still spaces and tabs only, so a NBSP-led line's tab is content. |
| `is_blank` | Unchanged; also used by the line visitor's blank check, so the two definitions cannot drift. |

---

## Exceptions (`src/syml/exceptions.py`)

| Class | Change |
| --- | --- |
| `ParseError` | Constructor gains keyword-only `filename: StrPath \| None = None`; stores private `_description`, `_filename`; public `.message` is the prefixed text; new `__str__` → `<loc>: <description>\n<line_text>` (R-07). |
| `OutOfContextNodeError`, `TabIndentationError`, `EncodingError`, `DuplicateKeyError` | Unchanged classes; every raise passes `filename=`. `DuplicateKeyError` keeps `key` and `first_position`. |
| `UnrepresentableValueError` | Unchanged (a `ValueError`, not a `ParseError`). |
| `DocumentLimitError` | Not added. §11.3 reserves the name (FR-017). |
| `error_message(description, filename)` | Treats `""` like `None`. |

---

## Serializer (`src/syml/serializer.py`)

| Element | Change |
| --- | --- |
| `dumps(data)` | `''` → `''`. Reads a `Source` key or scalar as its text before any type check (`str(value)` when `isinstance(value, Source)`). |
| `key_is_representable(k)` | `re.fullmatch(r'[a-z][a-z0-9_-]*', k)`; no grammar call, no comment-marker or uppercase check. |
| `_render_scalar_lines` | Enforces R-05's list; writes paragraph breaks as empty lines with no indentation; later lines unrestricted apart from R-05 items 4–5. |
| `_check_block_line` | Removed (its checks move into R-05's per-value rules). |
| `_lexes_as_structure(line)` | Matches `SymlParser.grammar['structure']` against `line.lstrip(' ')` with `parse` (full match), no `preprocess`; `RecursionError` still counts as structure. |
| `_COMMENT_MARKERS` | Removed. |

---

## API (`src/syml/__init__.py`)

| Element | Change |
| --- | --- |
| `loads(document, filename=None)` | `TypeError` for a non-`str` document. |
| `load(file_obj, filename=None)` | `TypeError` for a `read()` result that is neither `str` nor `bytes`, and for a non-decode `ValueError` from `read()`; filename from any `os.PathLike` `.name`. |
| `__all__` | Unchanged (no `DocumentLimitError`). |

---

## Validation rules, by requirement

| Rule | Where enforced | FR |
| --- | --- | --- |
| Key is `[a-z][a-z0-9_-]*` | grammar `key`; `key_is_representable` | FR-001, FR-002 |
| Text value absorbs lines at/past its threshold | `TextLeafNode.incorporate_node` | FR-003 |
| Blank lines inside a value kept one for one | `TextLeafNode.add_node` / `as_data` | FR-004 |
| Root scalar keeps leading indentation, baseline 0 | `Root.incorporate_node` / `add_node` | FR-005 |
| `dumps` residual set | `_render_scalar_lines` | FR-006 |
| No comments | grammar (no `comment` rule) | FR-007 |
| Tab is separator whitespace | grammar `ws` | FR-008 |
| Only U+0020 is indentation | grammar `indent`; line visitor's blank check | FR-009 |
| Children strictly deeper | `ContainerNode.can_add_node` (no `KeyValue` override) | FR-010 |
| `str(ParseError)` format | `ParseError.__str__` | FR-011 |
| Open columns and hints | `Root.fail_to_incorporate_node` | FR-012 |
| Filename prefix, original positions | every raise site; `preprocess` ordering | FR-013 |
| `dumps` reads `Source` as text | `dumps` / renderers | FR-014 |
| Input type guards, `PathLike`, `dumps('')`, blank-doc `Source` | `loads`, `load`, `_resolve_filename`, `dumps`, `Pos.from_str_index` | FR-017 |
