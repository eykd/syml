# Contract 02 — The §4.1 grammar and per-line lexing

**Requirements**: FR-004, FR-009 | **User stories**: US3, US5
**Spec**: §4.1, §4.4, §4.5, §4.6, §7.5, §7.6 | **Decisions**: D5, D6, D15, D16
**Audit gaps**: 7, 9, 13, 20 | **`todo.txt`**: A5, A10, B1, S1–S3

> No fenced example below carries a literal trailing space; `␠` marks one.

## Grammar

Transcribed from §4.1 as printed, with **two** substitutions — see "Escaping
inside `~"..."` atoms" below. Both are transcription-level, not normative.

```peg
document       = (line "\n")* line?
line           = indent (comment / structure / data)
structure      = list_item / key_value / section
indent         = ~" *"
comment        = ("#" / "//") text?
list_item      = ("-" ws value) / ("-" &eol)
key_value      = (key_colon ws? quoted_value ~" *") / (key_colon ws data)
section        = key_colon &eol
key_colon      = key ":"
key            = ~"[^\x00-\x20\x7f-\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000:]+"
eol            = &"\n" / ~"\\Z"
ws             = ~" +"
text           = ~"[^\n]*"

value          = structure / (quoted_value ~" *") / data
data           = text

quoted_value   = single_quoted / double_quoted
single_quoted  = "'" ("''" / ~"[^'\n]")* "'"
double_quoted  = '"' (escape_seq / ~"[^\"\\\\\n]")* '"'
escape_seq     = ('\\' ~"[\\\\/\"nrt]") / ('\\u' ~"[0-9a-fA-F]{4}") / ('\\U' ~"[0-9a-fA-F]{8}")
```

### Deltas from today's grammar and why each matters

| Today | Spec | Consequence of the change |
| --- | --- | --- |
| `lines = line*` | `document = (line "\n")* line?` | D16; removes nullable repetition |
| `indent = ~"\s*"` | `indent = ~" *"` | whitespace-only lines stop corrupting levels (audit gap #13, B1, US3 scenario 8) |
| `ws = ~"[ \t]+"` | `ws = ~" +"` | a tab is never separator whitespace (D5, US3 scenarios 5–6) |
| `text = ~".+"` | `text = ~"[^\n]*"` | matches empty, so `key:␠` lexes (D6, audit gap #6, US3 scenario 7) |
| `key = ~"[^\s:]+"` | enumerated class | D15 + kills both `SyntaxWarning`s (audit gap #20, FR-017, R-01) |
| `eol = "\n" / ~"$"` | `&"\n" / ~"\\Z"` | D16 (absolute end, lookahead-only) + the `\Z` escaping trap below |
| `list_item = "-" ws value` | `("-" ws value) / ("-" &eol)` | bare `-` takes a block value (§4.6, US3 scenario 1) |
| no `&eol` on `section` | `key_colon &eol` | `key:value` falls through instead of stranding (§7.6, US3 scenario 3) |
| no quoting | `quoted_value` alternatives | Contract 04 |
| separate `blank` rule | none | per §4.4 a space-only blank line is a `data` match of `""`; a tab-bearing one is not (`"\t"` is non-empty `data`), so blanks are dropped by `is_blank` before lexing (entry point below, D14) |

### Escaping inside `~"..."` atoms

Parsimonious evaluates the body of every `~"..."` atom as a **Python string
literal** before compiling it as a regex. Any sequence that is not a valid
Python escape emits `SyntaxWarning: invalid escape sequence` on import — and
under `-W error` it becomes a `VisitationError` wrapping a `SyntaxError`, so the
grammar does not load at all. Verified 2026-09-21.

Two atoms in §4.1 as printed are affected:

| As printed | As transcribed | Why |
| --- | --- | --- |
| `key = ~"[^\s:\x00-\x1f\x7f-\x9f]+"` | enumerated `White_Space` class, no `\s` | D15 requires the exact set (R-01); `\s` is also one of today's two `SyntaxWarning`s |
| `eol = &"\n" / ~"\Z"` | `~"\\Z"` | `\Z` is not a valid Python escape; **verified** to raise `VisitationError(SyntaxError)` under `-W error` |

Every other atom is safe: `\n`, `\"`, `\\\\`, `\x..`, and `\u....` are all valid
Python escapes. `\Z` is the only remaining landmine, and it is the same defect
class as audit gap #20 — so the FR-017 test obligation
(`python -W error -c "import syml"`) must pass with the grammar loaded, not just
with the module imported lazily.

### Key class

R-01 establishes that Python `re`'s `\s` and D15's `White_Space` set differ by
exactly `{U+001C..U+001F}`, and those four are inside `\x00-\x1f`, which the key
class already excludes. The enumerated class above is therefore behaviourally
identical to `[^\s:\x00-\x1f\x7f-\x9f]+` under CPython while satisfying D15's
"MUST use this exact set" literally and emitting no `SyntaxWarning`.

`a\x01b: v` does **not** lex as a key-value pair (US3 scenario 9, `todo.txt` A5);
it falls through to `data`.

## Entry point — per-line lexing (R-09)

`document` stays in the grammar text for fidelity with §4.1 and D16, but is
**not** the parse entry point. Parsing is:

```python
doc = preprocess(text, filename)            # Contract 01
visitor = SymlParser(doc)                   # holds position_map, original, filename
root = tip = Root(pnode=None, source=Source(  # Contract 03: no document-level pnode
    filename=doc.filename, start=Pos(0, 1, 0), end=Pos(0, 1, 0), text=''))
for line in split_lines_lf(doc.normalized): # §9.1 step 2
    if is_blank(line.text):                 # D14: discarded before any other check
        continue
    pnode = GRAMMAR['line'].match(line.text)  # §9.1 step 3 — match, not parse
    if pnode.end < len(line.text):            # stranded: §4.7 trailing content
        raise_trailing_content(pnode, line, doc)  # Contract 05 — anchors at the opening quote
    visitor.line = line                       # NodeVisitor.visit takes ONE argument
    node  = visitor.visit(pnode)
    if isinstance(node, Comment):             # D12: never incorporated (data-model §2)
        tip.comments.append(node)
        continue
    tip   = tip.incorporate_node(node, doc)   # Contract 03
return root
```

**The comment branch is load-bearing.** `Comment` is a `TextLeafNode`
subclass (data-model §3), and `TextLeafNode.can_add_node` accepts any
`TextLeafNode`. An unrouted comment would therefore join a value as
continuation text (`"key: a\n  # c\n  b"` → `"a\n# c\nb"`, breaking D12),
or become the root scalar of a comment-only document. Today's `visit_lines`
has the same `isinstance(child, Comment)` branch, and the per-line loop keeps
it.

**The blank-line skip is load-bearing, not an optimization.** A tab-bearing
blank line (`"  \t  "`) lexes as `indent` + a **non-empty** `data` (`"\t  "`),
so the grammar alone cannot classify it as blank; only `is_blank` can
(Contract 01). With the skip in place, the grammar's `data`-matches-`""` path
is unreachable from this loop. `is_blank` is the same function step 3's tab
scan uses, so the two cannot disagree about which lines are blank.

**How the visitor learns the line.** `NodeVisitor.visit(node)` takes exactly
one argument (verified: `visit(pnode, line)` is a `TypeError`), and a per-line
`pnode.full_text` is the **line**, not the document (verified). So the visitor
is built once per document holding the `Document`, and the loop sets
`visitor.line` before each `visit`. Every node's `Source` is built from that
line (Contract 08's `Source.from_node(pnode, line, position_map, filename)`);
nothing reads `pnode.full_text` for positions.

**`SymlParser.__init__` signature change from today:** `SymlParser(filename:
StrPath | None = None)` becomes `SymlParser(doc: Document)`. `filename` is
still reachable as `doc.filename` (Contract 01); the constructor takes the
whole `Document` because `Source.from_node` needs `position_map` too, and
`visitor.line` is set per-iteration as a plain mutable attribute, not a
constructor argument.

`match` rather than `parse`: `parse` is `match` plus a full-consumption check
whose `IncompleteParseError` carries only the strand point, while the error
must anchor at the opening quote. Contract 05 gives the detail.

This makes §5.1 rule 6 ("each line is lexed independently of its position in the
document") structural rather than incidental, and it gives the third-party
exception boundary a single, well-typed meaning — see Contract 05.

Line-local offsets are lifted with Contract 01's `pos_at(line, offset)`, so
`pos_at(line, pnode.start)` is the normalized `Pos` (index `line.start +
pnode.start`, line `line.number`, column `pnode.start`), which
`PositionMap.to_original` then maps to the original.

### `data` is an alias, and does not appear in the parse tree

`data = text` is a bare rule reference, and Parsimonious resolves it to the
**same expression object** as `text` (verified 2026-09-23:
`GRAMMAR['data'] is GRAMMAR['text']`, and a parse of `k: v` yields a node named
`text`, never `data`). Consequences for the visitor:

- `visit_data` never dispatches. Anything specified as happening "on a `data`
  match" is implemented on the node named `text`.
- `comment = ("#" / "//") text?` shares the same expression, so a `visit_text`
  hook also fires for comment bodies. It must not carry the quote-guard.
- The quote-guard (Contract 04) therefore lives in `visit_key_value` and
  `visit_list_item`, which know which alternative matched and can inspect their
  own `text` child — **not** in a `visit_data`/`visit_text` method. Root-scalar
  and continuation lines reach `text` through `line`, never through those two
  visitors, which is what keeps them exempt (D2).

Do not "fix" this by renaming grammar rules: the grammar is a transcription of
§4.1 and stays one.

### Zero-length inline values are dropped by the visitor (D6, §9.3)

The grammar cannot express D6: `key:␠` and `-␠` both lex with an **empty**
`text` child (the lexing table below). §9.3 normalizes a zero-length
*unquoted* inline value to "no inline value at all", so `visit_key_value`
(second alternative) and `visit_list_item` (`"-" ws value` whose `value` is
an unquoted `TextLeafNode`) **skip** the inline `incorporate_node` call when
that leaf's text is `""`, and return the still-empty `KeyValue` / `ListItem`.
The node stays open: a following block line or nested structure is accepted
exactly as after `key:` / `-`. A quoted value is never normalized — `key: ""`
and `- ''` are real children and close the node (§4.7). The quote-guard runs
first and cannot fire on an empty `text`.

## Level computation (R-11, §9's "Level" definition)

A node's `level` is the 0-indexed column where **its own** marker or content
begins: `pnode.start` (line-local) for the node's own token, **not** the line's
`indent` token.

Today `visit_line` does `value.set_level(indent.level)` and `set_level` recurses
into children, so a structure nested inline on a list-item line inherits the
line's indent. That is audit gap #14 / M23 exactly:

| Input | Today | Spec |
| --- | --- | --- |
| `"-   name: Alice\n  role: admin"` | `[{'name': 'Alice', 'role': 'admin'}]` | `OutOfContextNodeError` — `name`'s column is 4 (US1 scenario 8) |
| `"- name: Alice\nrole: admin"` | parses | `OutOfContextNodeError` |
| `"- name: Alice\n  role: admin"` | parses | parses — `name` is at column 2 |

### Who sets `level`, and when (red-team pass 11)

`level` is a **required constructor argument** (`level: int`, no `None`), set
by the `visit_*` method that builds the node, from that node's **own**
line-local `pnode.start`:

| Node | Built by | `level =` |
| --- | --- | --- |
| `KeyValue` | `visit_key_colon` (`section` and both `key_value` alternatives reach it) | the `key_colon` node's `start` — the key's column |
| `KeyLeafNode` | `visit_key` | the `key` node's `start` (never incorporated; carried for `Source` only) |
| `ListItem` | `visit_list_item` | the `list_item` node's `start` — the `-` column |
| `TextLeafNode` (unquoted) | `visit_text` | the `text` node's `start` |
| `TextLeafNode` (quoted) | `visit_quoted_value` | the `quoted_value` node's `start` — the opening quote |
| `Comment` | `visit_comment` | the `comment` node's `start` (never incorporated) |
| `Mapping` / `List` intermediary | §9.4 auto-creation (Contract 03) | the triggering node's `level` |
| `Root` | the per-line loop | `0` |

Parsimonious visits bottom-up, so every child node — with its `level` — exists
before the parent's `visit_*` runs. That ordering is what makes the **inline**
`incorporate_node` calls inside `visit_key_value` / `visit_list_item`
(Contract 05 rule 2) sound: both operands already carry their final level at
the moment of the call. Nothing assigns or reassigns `level` afterwards:
`set_level` is **deleted**, `visit_line` no longer touches levels (it returns
its structure/data child unchanged), and `IndentNode` / `visit_indent` become
dead and are removed. Today's `node.level is None or …` guards in
`can_add_node` and the `node.set_level(self.level)` inheritance in `add_node`
are deleted with them — the inheritance **is** M23, and without the guards a
`None` would reach `>`/`==` as a `TypeError`, which Parsimonious wraps in
`VisitationError` (not in `unwrapped_exceptions`), breaking FR-009.

Worked trace, `"-   name: Alice\n  role: admin"` (US1 scenario 8), line 1:
`visit_text` → `TextLeafNode(level=10)`; `visit_key_colon` → `KeyValue(level=4)`;
`visit_key_value` → `KeyValue(4).incorporate_node(TextLeafNode(10))` (10 > 4,
accepted); `visit_list_item` → `ListItem(level=0)`, then
`ListItem(0).incorporate_node(KeyValue(4))` → auto-creates `Mapping(level=4)`
(0 < 4) and adds the `KeyValue` to it; the tip is the `Alice` leaf. Line 2:
`KeyValue(level=2)` walks up past that leaf (not a `TextLeafNode`), the closed
`KeyValue(4)`, `Mapping(4)` (2 ≠ 4), the closed `ListItem(0)`,
`List(0)` (not a `ListItem`), and `Root` (not empty) →
`OutOfContextNodeError`.

## Lexing outcomes (§7.6 table plus the audit's additions)

| Input line | Lexes as | Result |
| --- | --- | --- |
| `key: value` | `key_value` | `{"key": "value"}` |
| `key:` | `section` | key with no inline value |
| `key:␠` | `key_value` (second alternative, **empty** `text` at column 5 — not `section`, whose `&eol` fails on the space; verified) | normalized by the visitor to no inline value (D6, below) — identical to `key:`, US3 scenario 7 |
| `key:value` | `data` | scalar `"key:value"` — US3 scenario 3 |
| `key:\tv` | `data` (D5) | scalar `"key:\tv"` — US3 scenario 5 |
| `key: \tv` | `key_value` | `{"key": "\tv"}` — US3 scenario 6 |
| `key:"value"` | `key_value` (quoted, `ws?`) | `{"key": "value"}` — §7.5 |
| `-` | `list_item` (`&eol`) | takes a block value — US3 scenario 1 |
| `-␠` | `list_item` (`ws value`, **empty** `text`) | normalized to no inline value (D6, below): one empty-string item when nothing follows (US3 scenario 2); `-␠\n  x` → `["x"]` |
| `-item` | `data` | scalar `"-item"` — US3 scenario 4 |
| `-42` | `data` | scalar `"-42"` |
| `- item # not a comment` | `list_item` | `["item # not a comment"]` (§4.3) |
| `#tag: value` | `comment` | comment wins over key (§4.3, §4.5) |
| `//x` | `comment` | |
| `invalid key: value` | `data` | key pattern rejects the space |
| `a\x01b: v` | `data` | control character excluded from keys |
| `"        "` (spaces only) | blank | dropped by `is_blank` before lexing; never affects indentation |
| `"  \t  "` (spaces and a tab) | blank | same — **never lexed**; lexing it would give non-empty `data` `"\t  "` |
| `k: 'a: b'` | `key_value` (quoted) | `{"k": "a: b"}` — `quoted_value` is tried first |
| `- 'a: b'` | `list_item` > `key_value` | `[{"'a": "b'"}]` — **§4.1 as printed**: `key` admits `'`, and `value` tries `structure` first (plan.md open item 4) |
| `- "a: b"` | `list_item` > `key_value` | `[{'"a': 'b"'}]` — same |
| `- 'a: b` (unterminated) | `list_item` > `key_value` | `[{"'a": "b"}]` — no error; the quote-guard never sees a quote-led `data` |
| `"a: b` (root) | `key_value` | `{'"a': "b"}` — same key class |

## Test obligations

- Every row of both tables above.
- `python -W error -c "import syml"` exits 0 (FR-017, audit gap #20).
- A grammar-load smoke test asserting `Grammar(...)` compiles without warnings.
- A test that `- "a` and `k: "a` raise `MalformedQuotedStringError` while
  `# "a` (comment) and `"a` (root scalar) do not — proving the quote-guard is
  not hung on the shared `text` expression.
- US3's nine acceptance scenarios.
- D6 through `loads`: `"key:␠\n  nested: content"` → `{"key": {"nested": "content"}}`;
  `"-␠\n  x"` → `["x"]`; `"- - ␠\n    x"` → `[["x"]]`; `"key: \"\"\n  x: y"` →
  `OutOfContextNodeError` (quoted empty is a real child).
- Level assignment: for `"-   name: Alice"`, the `ListItem`, `Mapping`,
  `KeyValue`, and `TextLeafNode` carry levels 0, 4, 4, 10; no node in any
  parsed tree has `level is None`.
- Through `loads`: `"  \t  \nkey: v"` → `{"key": "v"}` and
  `"key: a\n  \t\n  b"` → `{"key": "a\nb"}` (the `is_blank` skip; Contract 01).
- A two-line document's second-line key reports `line == 2` from
  `as_source()` — the per-line `full_text` trap above.
