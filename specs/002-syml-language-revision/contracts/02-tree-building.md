# Contract 02 — Tree Building: Text Context, Paragraph Breaks, Root Scalars, Strict Depth

**Requirements**: FR-003, FR-004, FR-005, FR-010 | **Decisions**: D21, D22, D25 (new); D11 affirmed; D12, D13 superseded | **Findings closed**: `syml-xreq.2`, `.3`, `.15`, `.20` (affirmed, no change), `.22`, `.21` (continuation half) | **Research**: R-01, R-03, R-04, R-06, R-12, R-13

## Surface

`syml.nodes` (`TextLeafNode`, `Root`, `KeyValue`) and therefore `loads`,
`load`, `parse(...).as_data()` / `.as_source()`. No public signature change.

```python
@dataclass(kw_only=True)
class TextLeafNode(SymlNode):
    inline: bool = False
    anchor_level: int = -1
    baseline: int | None = 0
    blank_lines_before: int = 0

    def accepts_level(self, level: int | None) -> bool: ...
    def can_add_node(self, node: SymlNode) -> bool: ...
    def incorporate_node(self, node: SymlNode) -> SymlNode: ...
    def add_node(self, node: SymlNode) -> SymlNode: ...
    def as_data(self) -> str: ...
    def as_source(self) -> Source: ...

@dataclass(kw_only=True)
class Root(ContainerNode):
    def incorporate_node(self, node: SymlNode) -> SymlNode: ...
    def fail_to_incorporate_node(self, node: SymlNode) -> NoReturn: ...  # Contract 03
```

`KeyValue` loses its `can_add_node` override; it inherits `ContainerNode`'s
`empty and node.level > self.level` for every node type.

## Rules

1. **Text context (FR-003).** `TextLeafNode.incorporate_node` overrides
   `SymlNode.incorporate_node`:

   ```python
   def incorporate_node(self, node: SymlNode) -> SymlNode:
       if (
           not isinstance(node, TextLeafNode)
           and node.content_pnode is not None
           and self.accepts_level(node.level)
       ):
           node = TextLeafNode(
               pnode=node.content_pnode,
               filename=node.filename,
               position_map=node.position_map,
           )
       return super().incorporate_node(node)
   ```

   The substitute carries the same `filename`/`position_map` as the node it
   replaces — both are threaded from the same `SymlParser`, so this only
   matters for consistency, not correctness. `super().incorporate_node`
   (`SymlNode.incorporate_node`) then re-checks `can_add_node(node)` itself:
   for the substituted node this is always `True` (the replacement only fires
   when `accepts_level` already held), so it is appended via `add_node`.
   `SymlNode.__post_init__` derives the substitute's `level` from
   `content_pnode.start.column` on the **normalized** text — the line's
   indentation width, the same value `node.level` already held — so no level
   is recomputed or lost in the swap. When the condition is false (the node
   is already a `TextLeafNode`, carries no `content_pnode`, or is below
   threshold), `super().incorporate_node` calls `self.can_add_node(node)`,
   finds it `False`, and delegates to `self.parent.incorporate_node(node)` —
   the original node walks up unchanged (§9.2), never the swapped one.
2. **Threshold.** `accepts_level(level)`: `False` for `None`; `level > anchor_level`
   while `baseline is None` (an inline value before its first continuation);
   `level >= baseline` after. D11 fixes the baseline as today.
3. **Structure is lexed only at a block's first line and inline.** A bare
   `key:` or `-` whose first block line lexes as structure gets that structure;
   one whose first block line is text opens a text value (rule 1 then applies).
   Inline values (`- - x`, `- key: v`) are unchanged.
4. **Paragraph breaks (FR-004, R-03, R-04).** On append,
   `blank_lines_before = full_text[prev.pnode.end : node.pnode.start].count("\n") - 1`,
   where `prev` is the value's last line (itself, or its last continuation).
   `as_data` emits that many `""` lines before the continuation. Blank lines
   before a block value's first line, after a value's last line, or between
   items/keys are never recorded.
5. **Root scalar (FR-005, R-12).** When `Root` is empty and offered a plain
   `TextLeafNode` from a physical line, it rebuilds it over `line_pnode`
   (column 0, indentation included); the leaf's baseline is 0. The document is
   then text throughout (rule 1, since every level is ≥ 0).
6. **Strict depth (FR-010).** A child must be strictly deeper than its parent;
   a `ListItem`/`List` under `key:` at the key's own column is no longer
   accepted. §6.2's `- key:` sibling-column rule is unchanged.

## Behaviour (source in → `as_data()` out)

| # | Input | Output |
| --- | --- | --- |
| US1-1 | `k:\n  Para one.\n\n  Para two.` | `{"k": "Para one.\n\nPara two."}` |
| US1-2 | `Para one.\n\nPara two.` | `"Para one.\n\nPara two."` |
| US1-3 | `k:\n  some prose\n  - used as a dash\n  more` | `{"k": "some prose\n- used as a dash\nmore"}` |
| US1-4 | `- Share is\n  //server/share` / `- tag line\n  #winning` | `["Share is\n//server/share"]` / `["tag line\n#winning"]` |
| US1-7 | `env:\n  HOME: /h\n  PATH: /p` | `{"env": "HOME: /h\nPATH: /p"}` |
| US1-9 | `Given:\n  a: 1` | `"Given:\n  a: 1"` |
| US1-10 | `  hello` / `  hello\nworld` / `  hello\n    world` | `"  hello"` / `"  hello\nworld"` / `"  hello\n    world"` |
| US1-11 | `k:\n  a\n\n\n  b\n\n` | `{"k": "a\n\n\nb"}` |
| US1-12 | `k:\n\n  a` | `{"k": "a"}` |
| US1-13 | `k:\n  a\n\nb: 2` | `{"k": "a", "b": "2"}` |
| US1-14 | `# one\n// two\n  # three` | `"# one\n// two\n  # three"` |
| US1-15 | `a:\n  b: 1\n  # note` | `OutOfContextNodeError` |
| US1-16 | `k: first\n  - second\n  key: third` | `{"k": "first\n- second\nkey: third"}` |
| US1-17 | `k:\n  - a\n  - b` / `k:\n  x: 1\n  y: 2` | `{"k": ["a", "b"]}` / `{"k": {"x": "1", "y": "2"}}` |
| US1-18 | `k: a\n    b\n  c` | `OutOfContextNodeError` |
| R-04 | `k: first\n\n  second` | `{"k": "first\n\nsecond"}` |
| R-03 | `k:\n  a\n      \n  b` | `{"k": "a\n\nb"}` |
| R-06 | `k:\n  a: 1\n   b: 2` | `{"k": {"a": "1\nb: 2"}}` |
| R-06 | `- eggs\n - bread` | `["eggs\n- bread"]` |
| edge | `hello\nk: v` / `---\nk: v` | `"hello\nk: v"` / `"---\nk: v"` |
| edge | `k: v\nhello` | `OutOfContextNodeError` |
| silent | `# Application config\nname: app\nport: 80` | `"# Application config\nname: app\nport: 80"` (a text first line makes the root text; no error, red team pass 1) |
| silent | `a:\n  # section\n  b: 1\n  c: 2` | `{"a": "# section\nb: 1\nc: 2"}` (a text first block line makes the block text) |
| silent | `-\tk: v\n        j: w` | `[{"k": "v\nj: w"}]` (the tab is one column; Contract 01) |
| silent | `name:\xa0app\nport: 80` | `"name:\xa0app\nport: 80"` (a NBSP after `key:` is not separator whitespace, so the first line is text and the root is text; raised at line 2 in 1.0; red team outer iteration 3) |
| silent | `server: # production\n  host: x\n  port: 80` | `{"server": "# production\nhost: x\nport: 80"}` (a `#` after `key:` is the inline text value, so the block under it joins it; raised in 1.0; red team outer iteration 5) |
| silent | `- # item note\n  name: x` | `["# item note\nname: x"]` (the same after `-`) |
| silent | `x: 1\nserver: \xa0\n  host: a\n  port: 80` / `- \xa0\n  name: x` | `{"x": "1", "server": "\xa0\nhost: a\nport: 80"}` / `["\xa0\nname: x"]` (a trailing invisible character after `key: ` or `- ` is a non-empty inline text value, FR-009, so the block under it joins it; raised in 1.0; red team outer iteration 6) |
| silent | `k: v\n \xa0\nj: w` / `k:\n  a\n  \xa0\n  b` / `k:\n  \x0c\n  b: 1` | `{"k": "v\n\xa0", "j": "w"}` / `{"k": "a\n\xa0\nb"}` / `{"k": "\x0c\nb: 1"}` (a line of only a NBSP, FF, or other non-space character is not blank, FR-009: indented at or past an open value's threshold it is a content line, and as a block's first line it makes the block text; 1.0 read all three as blank lines; red team outer iteration 8) |
| silent | `ports:\n  - containerPort: 80\n    protocol: TCP` | `{"ports": ["containerPort: 80\nprotocol: TCP"]}` (a non-pattern **first** key makes the item's inline value text, anchored at the `-` column; raised in 1.0) |
| edge | `- name: x\n  Age: 3` | `OutOfContextNodeError` at line 2 with hint (a) (a non-pattern **later** key sits at the open mapping's column; the contrast the README states, Contract 06 §D item 6) |
| recursion | `k:\n  a\n  ` + `"- " * 1000` + `x` | `RecursionError` (the per-line lex recurses before the text context applies; documented, not fixed; plan § Edge Cases) |
| US2-1 | `k:\n- a\n- b` | `OutOfContextNodeError` (hint, Contract 03) |
| US2-2 | `a:\n- x\n- y\nb: z` / `- key:\n  - x` | `OutOfContextNodeError` |
| edge | `- key:\n    - x` | `[{"key": ["x"]}]` |
| US2-3 | `- server:\n  host: x` | `[{"server": "", "host": "x"}]` (unchanged) |
| US2-7 | `k:\n  a\n\xa0\n  b` | `OutOfContextNodeError` |
| US2-14 | `key: v\n\xa0\tx` | `OutOfContextNodeError` (no `TabIndentationError`) |

`as_source()`: `str(node.as_source()) == node.as_data()` still holds, paragraph
breaks included. A root scalar `  hello` has `start == Pos(0, 1, 0)`.

## Fixtures (SC-003, R-13)

`tests/fixtures/bar.syml` lines 24 and 36 gain two spaces (`      - Bar >= 2`,
`      - Location = "Foyer"`); `tests/test_documents.py`'s expected tree is
unchanged. `stranger.syml` is unchanged.

## Test obligations

1. Every row above, as unit tests in `tests/test_nodes.py` /
   `tests/test_parsers.py`. The `US1-N` and `US2-N` rows are already the
   numbered acceptance scenarios in `spec.md` (18 for US1, 14 for US2 —
   `sp:05-tasks` binds them 1:1, no new scenario is added for them). The
   `R-03`, `R-04`, `R-06`, `silent`, and `edge` rows are **not** separately
   numbered in `spec.md` and stay unit-test-only pins in `tests/test_nodes.py`
   / `tests/test_parsers.py`; they are not additional US10/US11 Gherkin
   scenarios, so the 18/14 counts in the Acceptance Test Strategy table do
   not change. `R-04` in particular (`k: first\n\n  second` →
   `{"k": "first\n\nsecond"}`) is covered only here and by the SC-002
   round-trip property (Contract 04); it has no numbered `spec.md`
   acceptance scenario of its own, but FR-004 now carries the R-04 example
   inline (plan § Spec Corrections item 7) after planning found the
   original "between two continuation lines" wording read the opposite way
   for an inline value's first line.
2. `accepts_level` truth table: `None`; unset baseline at, above, below
   `anchor_level`; set baseline at, above, below.
3. SC-004: the four lane-4 documents (`doc01_scene_cellar`,
   `doc01b_scene_taxi` with `Given:` lowercased, `doc03_prose`,
   `doc03b_prose_root`) copied to `tests/fixtures/lane4/` and pinned to their
   ruled values. The ruled value is not the lane-4 `AUTHOR` column verbatim:
   `doc01b`'s `AUTHOR` has the key `'Given'`, but SC-004 loads the document
   with the header lowercased, so the pinned key is `'given'` (red team outer
   iteration 4).
4. The existing D11 baseline tests stay green unchanged (FR-003: "D11's
   baseline rule stands").
5. The nine `silent` rows are pinned as unit tests (US1's 18 acceptance
   scenarios stay as the spec writes them), so the release text's description of them (Contract 06 §B–§D)
   is checked against behaviour rather than asserted.
