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
| separate `blank` rule | none | a blank line is a `data` match of `""` (§4.1) |

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
for line in split_lines_lf(doc.normalized): # §9.1 step 2
    pnode = GRAMMAR['line'].parse(line.text)  # §9.1 step 3
    node  = visitor.visit(pnode, line)
```

This makes §5.1 rule 6 ("each line is lexed independently of its position in the
document") structural rather than incidental, and it gives the third-party
exception boundary a single, well-typed meaning — see Contract 05.

Line-local offsets are lifted to document offsets with `line.start`, so
`pnode.start + line.start` is the normalized index, which Contract 01's
`PositionMap` then maps to the original.

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

## Lexing outcomes (§7.6 table plus the audit's additions)

| Input line | Lexes as | Result |
| --- | --- | --- |
| `key: value` | `key_value` | `{"key": "value"}` |
| `key:` | `section` | key with no inline value |
| `key:␠` | `section` (D6) | identical to `key:` — US3 scenario 7 |
| `key:value` | `data` | scalar `"key:value"` — US3 scenario 3 |
| `key:\tv` | `data` (D5) | scalar `"key:\tv"` — US3 scenario 5 |
| `key: \tv` | `key_value` | `{"key": "\tv"}` — US3 scenario 6 |
| `key:"value"` | `key_value` (quoted, `ws?`) | `{"key": "value"}` — §7.5 |
| `-` | `list_item` (`&eol`) | takes a block value — US3 scenario 1 |
| `-␠` | `list_item` (`ws value`, empty `data`) | one empty-string item — US3 scenario 2 |
| `-item` | `data` | scalar `"-item"` — US3 scenario 4 |
| `-42` | `data` | scalar `"-42"` |
| `- item # not a comment` | `list_item` | `["item # not a comment"]` (§4.3) |
| `#tag: value` | `comment` | comment wins over key (§4.3, §4.5) |
| `//x` | `comment` | |
| `invalid key: value` | `data` | key pattern rejects the space |
| `a\x01b: v` | `data` | control character excluded from keys |
| `"        "` (spaces only) | blank | discarded in pre-processing; never affects indentation |

## Test obligations

- Every row of both tables above.
- `python -W error -c "import syml"` exits 0 (FR-017, audit gap #20).
- A grammar-load smoke test asserting `Grammar(...)` compiles without warnings.
- US3's nine acceptance scenarios.
