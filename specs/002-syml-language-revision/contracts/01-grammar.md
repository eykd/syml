# Contract 01 — The Grammar and Line Lexing

**Requirements**: FR-001, FR-007, FR-008, FR-009, FR-016 (§4.1 half) | **Decisions**: D20, D23, D24 (new); D14, D16 affirmed; D5, D15, D19 superseded | **Findings closed**: `syml-xreq.1`, `.9` (grammar half), `.16`, `.19`, `.21` (grammar half) | **Research**: R-02, R-11

## Surface

`syml.parsers.SymlParser.grammar` (a `parsimonious.Grammar`), the line and
document visitors, and the printed grammar in `SYML-SPECIFICATION.md` §4.1.
Neither `loads` nor `parse` changes signature.

### The grammar (code and §4.1 carry the same rule set)

```peg
document        = (line "\n")* line?
line            = indent (structure / data)
structure       = list_item / key_value / section
indent          = ~" *"
list_item       = value_list_item / guard_list_item
value_list_item = "-" ws value
guard_list_item = "-" &eol
key_value       = key_colon ws data
section         = key_colon &eol
key_colon       = key ":"
key             = ~"[a-z][a-z0-9_-]*"
eol             = &"\n" / ~r"\Z"
ws              = ~"[ \t]+"
text            = ~"[^\n]*"
value           = structure / data
data            = text
```

The §4.1 block may add comments and column alignment; rule content must be
identical. There is no `comment` rule and no `blank` rule.

`eol`'s regex is a **raw** literal (`~r"\Z"`). Parsimonious evaluates rule
literals as Python string literals, and `~"\Z"` emits
`SyntaxWarning: invalid escape sequence '\Z'`, which `pyproject.toml`'s
`filterwarnings = ["error::SyntaxWarning"]` turns into an import-time failure
of `SymlParser` (red team pass 1; the planning spike fails this way). Both
spellings give the same `as_rule()` text (`~'\\Z'u`), so the identity test
is unaffected. `document` stays the first rule in both places: Parsimonious's
default rule is the first one.

### Visitor signatures (`src/syml/parsers.py`)

```python
class SymlParser(NodeVisitor):
    def visit_document(self, node: Node, children: list[object]) -> nodes.Root: ...
    def visit_line(self, node: Node, children: list[object]) -> nodes.SymlNode | None: ...
    def visit_key_value(self, node: Node, children: SymlNodes) -> nodes.KeyValue: ...
    def visit_section(self, node: Node, children: SymlNodes) -> nodes.KeyValue: ...
    def visit_key_colon(self, node: Node, children: SymlNodes) -> nodes.KeyValue: ...
    def visit_value_list_item(self, node: Node, children: SymlNodes) -> nodes.ListItem: ...
    def visit_guard_list_item(self, node: Node, children: SymlNodes) -> nodes.ListItem: ...
    def visit_text(self, node: Node, children: SymlNodes) -> nodes.TextLeafNode: ...
    def visit_key(self, node: Node, children: SymlNodes) -> nodes.KeyLeafNode: ...
```

- `visit_line` returns `None` when the line's content span (after `indent`) is
  empty or `preprocess.is_blank`. Otherwise it sets `content_pnode` (the
  `(structure / data)` child's parse node) and `line_pnode` (the whole line's
  parse node) on the lexed node and returns it.
- `visit_document` flattens its visited children (`Node | list | None`,
  because `generic_visit` collapses single-child groups) and incorporates each
  line into the tip, starting from a fresh `Root`.
- Removed: `visit_lines`, `visit_blank`, `visit_comment`, `visit_indent`,
  `key_has_uppercase`, `_is_text_line`, `_text_leaf`, `_UPPERCASE_CATEGORIES`.

## Behaviour (source in → `as_data()` out)

Keys (FR-001):

| Input | Output |
| --- | --- |
| `choice1: x` / `first-name: x` / `first_name: x` | `{"choice1": "x"}` / `{"first-name": "x"}` / `{"first_name": "x"}` |
| `1: x` / `_x: x` / `-x: x` / `e.mail: x` / `名前: x` / `ß: x` / `URL: x` / `firstName: x` | the root scalar, verbatim |
| `- [ask: why?]` | `["[ask: why?]"]` |
| `- 3: 1 odds` | `["3: 1 odds"]` |
| `"so: you came back."` | `"\"so: you came back.\""` |

Separator whitespace (FR-008):

| Input | Output |
| --- | --- |
| `k:\tv` | `{"k": "v"}` |
| `k: \tv` | `{"k": "v"}` (was `{"k": "\tv"}`, R-11) |
| `a:\t` + newline + `  b: 1` | `{"a": {"b": "1"}}` |
| `- a` + newline + `-\tx` | `["a", "x"]` |
| `k: a\tb` | `{"k": "a\tb"}` (a tab after the value's first character is unchanged) |
| `-\tk: v` + newline + `  j: w` | `[{"k": "v", "j": "w"}]`: a column is a code-point count, so the tab is one column and `k` sits at column 2 (§6.2) |
| `-\tk: v` + newline + `        j: w` | `[{"k": "v\nj: w"}]`: eight spaces is past `k`'s column 2, so the line joins the inline value (D21), even where an editor shows it aligned under `k` |

Indentation (FR-009):

| Input | Output |
| --- | --- |
| `\xa0k: v` | `"\xa0k: v"` |
| `\x0bx` / `\x0c` / `\u2028- x` | `"\x0bx"` / `"\x0c"` / `"\u2028- x"` |
| `\xa0` | `"\xa0"` (a NBSP-only line is text, not blank) |
| `a:` + newline + `\tb` | `TabIndentationError` (unchanged) |
| `  \t  ` as a middle line | blank (skipped) |

No comments (FR-007): `# c` → `"# c"`; `port: 8080 # default` →
`{"port": "8080 # default"}` (unchanged).

Document shape: `k: v` and `k: v\n` both → `{"k": "v"}`; `""`, `"\n"`,
`"\n  \n\t\n"` → `""`.

## Test obligations

1. **Grammar identity**: a test loads §4.1's fenced `peg` block with
   `parsimonious.Grammar` and asserts `{name: rule.as_rule()}` equals the same
   map over `SymlParser.grammar` (SC-005, US4 scenario 2). It also asserts
   both grammars' `default_rule.name == 'document'`, and it runs under the
   repository's `error::SyntaxWarning` policy, so a non-raw escape in either
   grammar fails it.
2. One parametrized test per table above.
3. `visit_line` returns `None` for `""`, `"   "`, `"\t"`, `" \t "` content
   spans and not for `"\xa0"`.
4. The grammar leaf is atomic (R-02): top rule, `indent`, `ws`, `key`, `eol`,
   and the `comment` removal land together; the suite is green at that commit.
5. **Coverage at the grammar-leaf commit** (red team outer iteration 5):
   `tests/test_nodes.py::TestSymlNodeBaseStubs` reaches `SymlNode.as_data`,
   `.as_source`, `.can_add_node`, and `.fail_to_incorporate_node` only
   through `IndentNode`, which this leaf deletes, and
   `SymlNode.fail_to_incorporate_node` does not move to `Root` until the
   error leaf (Contract 03). The grammar leaf rewrites those four tests over
   a test-local bare `SymlNode` subclass (or `SymlNode` itself) and deletes
   the `Comment` test in `TestDirectTestsForPreviouslyPragmadBranches`, so
   100% branch coverage holds at this commit without a pragma.
