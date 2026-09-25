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

1. **Text context (FR-003).** When a `TextLeafNode` is the tip and is offered
   a non-`TextLeafNode` that carries a `content_pnode` and whose level passes
   `accepts_level`, it is replaced by `TextLeafNode(pnode=node.content_pnode)`
   and appended. Otherwise the node walks up unchanged (§9.2).
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
   round-trip property (Contract 04); it has no `spec.md` acceptance scenario
   of its own because FR-004's continuation-line wording already reads that
   the inline value's text counts as the value's first line (R-04's ruling),
   so no example was added there.
2. `accepts_level` truth table: `None`; unset baseline at, above, below
   `anchor_level`; set baseline at, above, below.
3. SC-004: the four lane-4 documents (`doc01_scene_cellar`,
   `doc01b_scene_taxi` with `Given:` lowercased, `doc03_prose`,
   `doc03b_prose_root`) copied to `tests/fixtures/lane4/` and pinned to their
   ruled values.
4. The existing D11 baseline tests stay green unchanged (FR-003: "D11's
   baseline rule stands").
5. The three `silent` rows are pinned as unit tests (US1's 18 acceptance
   scenarios stay as the spec writes them), so the release text's description of them (Contract 06 §B–§D)
   is checked against behaviour rather than asserted.
