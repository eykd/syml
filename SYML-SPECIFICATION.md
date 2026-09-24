# SYML Specification

**Version:** 1.0
**Status:** Released specification. The `syml` Python package (1.0.0) is the
conforming reference implementation; §2-§13 are authoritative.

---

## 1. Introduction

SYML (Simple YAML-like Markup Language) is a lightweight, structured document markup language with YAML-like syntax but fundamentally simpler semantics. SYML deliberately avoids YAML's complexity and type coercion features in favor of predictable, string-only leaf values.

### 1.1 Design Philosophy

1. **All leaf values are strings** - No automatic type conversion (integers, floats, booleans, dates, etc.)
2. **Indentation-based structure** - Nesting is determined by whitespace indentation
3. **Minimal features** - No anchors, aliases, tags, or complex constructs
4. **Predictable parsing** - Same input always produces same output
5. **Source preservation** - Full tracking of source locations for debugging

> **Note:** SYML has no quoted strings and no escape sequences. Every value is the literal text on the page: a `'` or `"` is an ordinary character wherever it appears, so dialogue such as `- "Late for what?"` keeps its quotation marks. A value that must span lines is written in block form (§5).

### 1.2 Comparison with YAML

| Feature | SYML | YAML |
|---------|------|------|
| Type coercion | No | Yes |
| Anchors & aliases | No | Yes |
| Tags | No | Yes |
| Flow collections | No | Yes |
| Multi-document support | No | Yes |
| String values | All leaves | Type-dependent |

---

## 2. Document Structure

A SYML document is a sequence of **lines**. Each line contains optional indentation followed by one of:

- A **comment**
- A **blank line**
- A **structure** (list item, key-value pair, or section header)
- A **scalar value** (continuation text)

### 2.1 Root Element

A SYML document has exactly one root element, which may be:

- A **scalar** (plain text value)
- A **list** (sequence of items)
- A **mapping** (collection of key-value pairs)

```
# Scalar root
hello world

# List root
- item1
- item2

# Mapping root
key1: value1
key2: value2
```

---

## 3. Data Types

SYML supports exactly three data types:

### 3.1 Scalars (Strings)

All leaf values in SYML are **plain strings**. There is no automatic conversion of values like `true`, `false`, `null`, `123`, or `3.14` to their respective types.

```syml
booleans:
  - true
  - false
  - True
  - False

numbers:
  - 123
  - 3.14
  - -42

special:
  - null
  - ~
```

**Output (as JSON-like structure):**
```json
{
  "booleans": ["true", "false", "True", "False"],
  "numbers": ["123", "3.14", "-42"],
  "special": ["null", "~"]
}
```

### 3.2 Lists (Sequences)

Lists are ordered sequences of items, each prefixed with a hyphen (`-`) followed by whitespace.

```syml
- first item
- second item
- third item
```

**Output:** `["first item", "second item", "third item"]`

### 3.3 Mappings (Dictionaries)

Mappings are collections of key-value pairs. Implementations MUST preserve
insertion (source) order: keys MUST appear in the returned mapping in the
same order they first appear in the document. Consumers MAY rely on this
ordering when iterating a mapping returned by `loads`. Keys are separated
from values by a colon (`:`); at least one space MUST follow the colon
before an inline value (see §7.5).

```syml
name: Alice
age: 30
city: Wonderland
```

**Output:** `{"name": "Alice", "age": "30", "city": "Wonderland"}`

> **Note:** Examples show keys in insertion order; this order is
> guaranteed by this section, not merely illustrative.

---

## 4. Syntax Rules

### 4.1 Formal Grammar (PEG Notation)

The grammar below assumes §9.0's pre-processing (BOM stripping and
CRLF/CR line-ending normalization) has already been applied to the input;
no rule below needs to handle a bare `\r` or a leading BOM.

```peg
document       = (line "\n")* line?
line           = indent (comment / structure / data)
structure      = list_item / key_value / section
indent         = ~" *"              # Spaces only, no tabs (leading-tab scan is §9.0, before this grammar runs)
comment        = ("#" / "//") text?
list_item      = ("-" ws value) / ("-" &eol)    # A "-" is a marker only before whitespace or EOL
key_value      = key_colon ws data
section        = key_colon &eol             # A standalone section header must end the line
key_colon      = key ":"
key            = ~"[^\s:\x00-\x1f\x7f-\x9f]+"   # Printable, non-whitespace, non-colon (§4.5's \s is the Unicode White_Space set); see also the no-uppercase rule below
eol            = &"\n" / ~"\Z"              # Lookahead only: "\n" is consumed by `document`, never by `line`
ws             = ~" +"              # Required whitespace (spaces only; a tab does not satisfy this, see §7.5)
text           = ~"[^\n]*"          # Any characters to end of line (including empty)

value          = structure / data
data           = text               # Literal text: there is no quoted-string rule anywhere in this grammar
```

`document` is the top rule. It joins `line` matches with explicit literal
`"\n"` tokens rather than having each `line` consume its own trailing
newline, and its final `line` is optional so a document may or may not
end in a newline (§4.7). `eol` is used only as a zero-width lookahead
*inside* a line (after a bare `-` in `list_item`, or after `key:` in
`section`), to check that nothing else follows on the current line — it
is never itself consumed. There is no separate `blank` rule: a blank line
(§4.4) is simply a line whose `comment`/`structure` alternatives both
fail and whose `data` therefore matches the empty string.

**Values are literal text.** `value` (a list item's inline slot) and
`data` (everything else) are the plain characters to the end of the
line. There is no quoted-string rule, no escape sequence, and no
position at which a `'` or `"` means anything but itself: `key: "a"` is
the three-character value `"a"`, quotation marks included. Every physical
line in a document — a root scalar's lines, a block value's lines, and
any continuation line — is parsed via `line`'s own
`(comment / structure / data)` choice: it may become nested `structure`
(a `list_item`, `key_value`, or `section` — this is how a block value's
line can instead become a nested list or mapping, §7.3/§6.1), and if it
falls all the way through to `data` it is text, taken as written (§7.6).

**The no-uppercase key rule (normative, not expressible in PEG alone):**
in addition to matching the `key` pattern above, the text a `key_value`
or `section` would take as its key MUST contain no code point whose
Unicode General_Category is `Lu` (uppercase letter) or `Lt` (titlecase
letter). A conforming implementation applies this check outside the PEG,
to the `key` matched by `key_value` and by `section`, on every line. A
line whose would-be key fails it is lexed exactly as if both rules had
failed to match: it reaches `data` and is literal text (§4.5, §7.6).
Inside a list item's inline `value` the same fallthrough applies, so
`- Listen: here` is the item text `Listen: here` and `- Listen:` is the
item text `Listen:`, whereas `- listen: here` is an inline mapping
(§7.2). The rule applies to the key only; value text is unrestricted.

### 4.2 Indentation

Indentation determines the hierarchical structure of a SYML document.

**Rules:**
1. Indentation MUST use spaces only
2. Tab characters in indentation are a parse error (§8.4, detected by §9.0's pre-processing scan)
3. Tabs within values (after the initial content) are permitted. A value
   that begins with a tab (for example, the content immediately following
   the separator space in `key: \tv`) parses without error, but such a
   value is unrepresentable by `dumps` (§11.2.1 rule B), since a leading
   tab is easily confused with indentation by a reader and SYML has no
   escape for it.
4. Indentation level = number of leading space characters
5. Child elements MUST have greater indentation than their parent
6. Sibling elements MUST have equal indentation

```syml
parent:
  child1: value1
  child2:
    grandchild:
      value
```
**Output:** `{"parent": {"child1": "value1", "child2": {"grandchild": "value"}}}`

`parent` is at level 0. `child1` and `child2` are siblings at level 2
(children of `parent`); `child2` is a section header. `grandchild` is a
child of `child2` at level 4, and `value` is its block value at level 6.
(A key that already holds an inline value, such as `child2: value2`,
cannot also have nested children — see §9.3 and the `note: hello` example
in §5.3.)

**Invalid indentation (error):**
```syml
parent:
  child1: value
   child2: value
```
**Output:** `ERROR: OutOfContextNodeError` — `child2` is indented 3
spaces, which matches neither `child1`'s sibling level (2) nor any valid
child level of `parent` (§8.1).

### 4.3 Comments

Comments begin with `#` or `//` and continue to the end of the line. A
line beginning with `#` or `//` is always a comment, even if the remainder
would otherwise look like a key-value pair or list item — see §4.5's
exception.

```syml
# This is a comment
// This is also a comment
key: value  # This is NOT a comment (part of the value)
```

**Important:** Comment markers (`#`, `//`) appearing after a value are treated as part of the value, not as comments. Comments must be on their own line.

```syml
- item # not a comment
```
**Output:** `["item # not a comment"]`

A line that looks like a key-value pair but starts with `#` or `//` is
still a comment, not a key:

```syml
#tag: value
```
**Output:** `""` (the whole line is a comment; an otherwise-empty document is the empty string, §7.4)

### 4.4 Blank Lines

Blank lines (lines containing only whitespace) are ignored and do not
affect document structure. Per §4.1, there is no dedicated `blank` rule —
a blank line is simply a line whose `comment` and `structure`
alternatives both fail to match and whose `data` fallback matches the
empty string. A whitespace-only line is recognized as blank during
§9.0's pre-processing, before its leading whitespace is scanned for tabs
(§8.4): a tab on an otherwise-blank line does not raise
`TabIndentationError`.

```syml
- item1

- item2


- item3
```
**Output:** `["item1", "item2", "item3"]`

### 4.5 Keys

A `key:` token matches when the text before the colon:
- Contains no whitespace characters
- Contains no colons (`:`)
- Contains no control characters (U+0000-U+001F, U+007F-U+009F)
- Contains no uppercase or titlecase letter: no code point whose Unicode
  General_Category is `Lu` or `Lt` (checked outside the PEG, §4.1)
- MAY contain any other printable Unicode characters (lowercase and
  caseless letters, numbers, punctuation, emoji)
- Pattern: `[^\s:\x00-\x1f\x7f-\x9f]+` (printable non-whitespace, non-colon), plus the no-uppercase rule
- Keys MUST be unique within their mapping; duplicate keys are a parse error (§8.3)

A line whose text before the first colon does not match this pattern, or
contains an uppercase or titlecase letter, is not a key-value pair at all;
it is parsed as scalar text (see §7.6).

**Why no uppercase:** a colon after a capitalized word is how prose and
dialogue are written (`Listen: here's what you need`, `Warning: do not
touch`), and SYML values are literal text, so a key must be visibly
distinguishable from such a line. Lowercase keys (`listen:`, `warning:`,
`look-in-dark:`) are how mappings are written; a capitalized word before
the colon is always text. The check is by General_Category, not by a
letter's case mapping: `É` (Lu) and `ǅ` (Lt) disqualify a key, while a
caseless letter such as `名` or a letterlike number such as `Ⅻ` (Nl) does
not.

```syml
- Listen: here's what you need
```
**Output:** `["Listen: here's what you need"]` — `Listen` contains an
uppercase letter, so the line is not a `key_value`; it is the list item's
literal text.

```syml
Été: chaud
```
**Output:** `"Été: chaud"` — a root scalar, not a mapping.

```syml
look-in-dark: torch
effect: none
名前: value
```
**Output:** `{"look-in-dark": "torch", "effect": "none", "名前": "value"}`

**Residual hazard:** a prose line that begins with a *lowercase* word
followed by `: ` still lexes as a key-value pair (`note: see below` is a
mapping, never text). Authors writing prose in block form should
capitalize such a word or avoid the `word: ` shape; see §5.1 rule 6 and
§7.6.

**Exception:** A key may not begin with `#` or `//`. Per §4.1, `comment` is
tried before `structure` on every line, so a line starting with either
marker is always read as a comment (§4.3), regardless of whether the
remaining text would otherwise form a valid key. There is no way to write
a key beginning with `#` or `//` in this version (a quoted-key syntax is
a v1.2 candidate — see §11.2.3).

A key containing whitespace, `:`, or an uppercase or titlecase letter,
the empty-string key, or a key beginning with `#`/`//` cannot be produced
by `loads` (the grammar never recognizes such text as a key), and cannot
be produced by `dumps` either — see §11.2.3.

The `\s` in the key pattern above denotes exactly the set of code points
with the Unicode `White_Space` property: U+0009–U+000D, U+0020, U+0085,
U+00A0, U+1680, U+2000–U+200A, U+2028, U+2029, U+202F, U+205F, and
U+3000. Implementations MUST use this exact set, not a host regex
engine's default `\s` (some, such as Go's RE2 or Rust's `regex` crate,
default to ASCII-only whitespace, which would make a key containing
U+00A0 a valid key in one conforming implementation and an invalid one
in another).

```syml
simple-key: value
key_with_underscores: value
key.with.dots: value
key/with/slashes: value
booleans?: value
123: value
emoji🎉key: value
```

### 4.6 Values

Values are either:
- **Inline values** - Text following a key's colon or list item's hyphen on the same line
- **Block values** - Text on subsequent lines with greater indentation

```syml
# Inline value
key: inline value
```
**Output:** `{"key": "inline value"}`

```syml
# Block value
key:
  block value
```
**Output:** `{"key": "block value"}`

```syml
# List with inline values
- inline item
```
**Output:** `["inline item"]`

```syml
# List with block values
-
  block item
```
**Output:** `["block item"]`

#### 4.6.1 Control Characters in Values

Unlike keys (§4.5), value text MAY contain any Unicode code point except
the line-separator U+000A (excluded structurally, since it terminates a
line per §13.3). In particular, C0 and C1 control characters
(U+0000-U+001F, U+007F-U+009F) — other than the tab handling defined in
§4.2 rule 3 — ARE permitted verbatim in value text, including U+0000
(NUL), and implementations MUST pass them through unmodified. Applications
that hand SYML values to NUL-sensitive consumers (C APIs, shells, log
pipelines) SHOULD document this explicitly rather than silently stripping
or rejecting such characters, since silent stripping would violate §1.1's
predictable-parsing principle.

### 4.7 Line Endings

Line endings are normalized before parsing begins; §9.0 specifies the
exact pre-processing algorithm (BOM stripping and CRLF/CR normalization)
that a conforming implementation MUST perform. In summary:

- `\r\n` (CRLF, Windows) is converted to `\n` (LF)
- `\r` (CR, old Mac) is converted to `\n` (LF)
- Documents may end with or without a trailing newline

Normalization applies to the **entire document**. A value therefore
cannot contain a literal CR: there is no escape sequence to write one
(§4.1), and `dumps` treats a string containing `\r` as unrepresentable
(§11.2.1).

---

## 5. Multiline Values

When a scalar value spans multiple lines, continuation lines are joined with newline characters (`\n`).

### 5.1 Continuation Rules

1. Continuation lines MUST have greater indentation than the indentation
   level of the containing key-value pair or list item. A scalar value at
   the document root, with no containing key-value pair or list item,
   uses an implicit reference level of −1 for this rule, so any line at
   level ≥ 0 may continue it.
2. The indentation reference point is the key or list marker, not the inline value
3. Multiple continuation lines are joined with `\n`
4. A continuation line that begins with `#` or `//` (after its own
   indentation) is parsed as a comment (§4.3) and is skipped: it does not
   contribute to the value and does not terminate the continuation block,
   at any indentation. A multiline value with a line that begins with `#`
   or `//` therefore has no SYML encoding: such a value is
   unrepresentable by `dumps` (§11.2.1). (A single-line inline value may
   begin with `#` or `//`: `- #x` is the item `#x`, §4.3.)
5. A blank or whitespace-only line inside a multiline value is discarded
   the same way: it neither adds an empty line to the value nor
   terminates it, regardless of its own indentation. A value that must
   contain a blank line (a paragraph break) cannot be written using block
   continuation at all, and since SYML has no escape sequences it has no
   encoding: such a value is unrepresentable by `dumps` (§11.2.1).
6. Every physical line is lexed independently of its position in the
   document (§4.1): a line at a continuation position that itself parses
   as `list_item`, `key_value`, or `section` is that structure, not
   literal continuation text, regardless of how it looks in context. See
   §7.6 and §6.4 for what this means when such a line cannot attach
   anywhere.

```syml
key: first line
  second line
  third line
```
**Output:** `{"key": "first line\nsecond line\nthird line"}`

In the above example, `key:` is at column 0, so continuation lines must be indented beyond column 0.

A root-level scalar with no containing key or list item joins across
lines the same way, using the implicit reference level of −1 from rule 1:

```syml
hello
world
```
**Output:** `"hello\nworld"`

### 5.2 Multiline in Lists

```syml
- first item
- second item
  continues here
  and here
- third item
```
**Output:** `["first item", "second item\ncontinues here\nand here", "third item"]`

### 5.3 Indentation Preservation

The **baseline** for a multiline value is the indentation level of the
first line of the value that occupies **a line of its own**, except for a
root scalar, whose baseline is always 0:

- For an **inline** value (`key: first`/`- first`), that is its first
  **continuation** line — the first physical line after the one holding
  `key:`/`-` that is accepted as part of the value. The inline text
  itself (`first`) shares its line with the key/marker and does not set
  the baseline.
- For a **block** value (`key:`/`-` alone, value on subsequent lines),
  that is its first **block** line — unlike the inline case, this line
  already occupies a line of its own, so it sets the baseline
  immediately; there is no separate "first line doesn't count" step for
  block form.
- For a **root scalar**, the baseline is fixed at level 0, whatever its
  first line's indentation. That first line's own indentation beyond 0 is
  preserved as literal leading whitespace, exactly like any later line:
  `  hello\nworld` is `"  hello\nworld"`, and the one-line document
  `  hello` is `"  hello"`.

In every case, this first own-line must be strictly deeper than the
anchor — the level of the containing key-value pair or list item, or −1
for a root scalar (§5.1 rule 1) — to be accepted as part of the value at
all. Once the baseline is set, subsequent lines:

- At or beyond the baseline: joined, with any indentation beyond the
  baseline preserved as literal leading whitespace in the joined text.
- Below the baseline: not a continuation of this value. The line
  terminates the value at the previous line and is instead offered to
  the value's owning key-value pair, list item, or the root, as an
  ordinary new line — exactly as if the multiline value had ended one
  line earlier (§9.2, §9.3). This may succeed (for example, as a new
  sibling key at a shallower, valid level) or fail with
  `OutOfContextNodeError` (§8.1/§8.2), depending on whether any enclosing
  level actually matches it.

```syml
key:
  first
    indented
  back
```
**Output:** `{"key": "first\n  indented\nback"}`

This is a block value: `first` is its first block line and sets the
baseline to 2 immediately. `indented` is 2 spaces beyond the baseline, so
those 2 extra spaces are preserved. `back` returns to the baseline and
joins as-is.

```syml
key:
  a
 b
```
**Output:** `ERROR: OutOfContextNodeError`

`a` sets the baseline to 2. `b` (level 1) is below that baseline and
terminates the value at `"a"`, but `key`'s KeyValue is already closed
(§9.3) and there is no level-1 sibling or child context for `b` to
attach to, so the line is out of context and the whole document is a
parse error.

```syml
hello
  world
again
```
**Output:** `"hello\n  world\nagain"`

This is a root scalar: the baseline is fixed at 0 regardless of `hello`'s
own level. `world` (level 2) is beyond the baseline, so its 2 extra
spaces are preserved. `again` (level 0) is at the baseline and joins
as-is.

```syml
key: a
    b
  c
```
**Output:** `ERROR: OutOfContextNodeError`

This is an inline value: `a` shares `key`'s line and does not set the
baseline. `b` is the first continuation line and sets the baseline to 4.
`c` (level 2) is below that baseline and terminates the value at
`"a\nb"`, but `key`'s KeyValue is already closed and there is no level-2
sibling context for `c` to attach to, so the line is out of context and
the whole document is a parse error.

A continuation candidate at exactly the containing key/item's own level
is not a continuation at all (§5.1 rule 1 requires strictly greater
indentation), and a line that syntactically parses as its own structure
(a full `key: value`) is never a TextLeaf continuation regardless of
level — a KeyValue or ListItem that already holds a value is closed
(§9.3) to any further content, and every line is lexed independently of
its position (§5.1 rule 6):

```syml
key: a
b
```
**Output:** `ERROR: OutOfContextNodeError`

```syml
note: hello
  more: text
```
**Output:** `ERROR: OutOfContextNodeError`

`more: text` lexes as a valid `key_value` (`more` has no whitespace and
no uppercase letter, so it is a valid key) regardless of it looking like a continuation of
`note`'s prose; being deeper than `note`, it is offered as a child of
`note`'s KeyValue, which is already closed by the inline value `hello`,
so it raises. See §7.6 for the contrasting case where the text before
the colon is not a valid key.

---

## 6. Nesting

Structures can be nested arbitrarily deep.

### 6.1 Lists in Mappings

```syml
shopping:
  - apples
  - bananas
  - oranges
```
**Output:** `{"shopping": ["apples", "bananas", "oranges"]}`

### 6.2 Mappings in Lists

```syml
- name: Alice
  role: admin
- name: Bob
  role: user
```
**Output:**
```json
[
  {"name": "Alice", "role": "admin"},
  {"name": "Bob", "role": "user"}
]
```

A key written inline after a list marker (`- name: Alice`) is an
ordinary `KeyValue` node whose level is the column where `name` itself
begins — not the column of the `-`. Any sibling key nested under the
same list item MUST start at that exact column, regardless of how many
spaces followed the `-`:

```syml
-   name: Alice
    role: admin
```
**Output:** `[{"name": "Alice", "role": "admin"}]`

Here `name` begins at column 4 (three spaces after the marker), so
`role` must also begin at column 4 — two spaces after `-` (as in the
first example above) would not match and would raise
`OutOfContextNodeError` (§8.1).

### 6.3 Deep Nesting

```syml
level1:
  level2:
    - item1:
        nested: value
    - item2:
        - deeply
        - nested
        - list
```
**Output:**
```json
{
  "level1": {
    "level2": [
      {"item1": {"nested": "value"}},
      {"item2": ["deeply", "nested", "list"]}
    ]
  }
}
```

### 6.4 Mixed Content at Same Level

At any given indentation level, content must be homogeneous:
- Either all list items (`-`)
- Or all key-value pairs (`key:`)

This is enforced by §9.3's node acceptance rules: a List's acceptance
test never accepts a KeyValue, and a Mapping's never accepts a ListItem,
so mixing structure types at the same level always fails every
acceptance test up the tree and raises `OutOfContextNodeError` (§8.2).
The same reasoning makes a plain-text line at a container's own level an
error too, even though it is neither a ListItem nor a KeyValue: a
Mapping only ever accepts a KeyValue as a sibling, so a `data`-only line
at that level has nowhere valid to attach (§9.3).

**Invalid (mixing at same level):**
```syml
- list item
key: value
```
**Output:** `ERROR: OutOfContextNodeError` — a Mapping's `key: value` cannot become a sibling of a List's items.

**Invalid (plain text at a mapping's level):**
```syml
a:
  b: 1
  plain
```
**Output:** `ERROR: OutOfContextNodeError` — `plain` is not a valid
`key_value` (no colon), so it cannot join the Mapping under `a` as a
sibling of `b`; it is also not a TextLeaf continuation of anything (`b`'s
own KeyValue is closed, and `a`'s KeyValue holds a Mapping, not a
TextLeaf), so it has nowhere to attach.

---

## 7. Edge Cases and Clarifications

### 7.1 Inline Colons in Values

After the first colon that separates key from value, additional colons are part of the value:

```syml
url: https://example.com:8080/path
```
**Output:** `{"url": "https://example.com:8080/path"}`

### 7.2 Inline List Syntax (Not Supported As a Distinct Notation)

SYML does not support flow/inline collection syntax as a separate
notation, but a leading `-` in a value is handled differently depending
on where the value occurs.

**In a mapping value** (after `key:`), a leading `-` is always literal
text. `key_value`'s grammar (§4.1) never re-enters `structure` for the
inline portion of a mapping's value — it matches `data` directly — so
this stays literal no matter what follows the `-`:

```syml
key: - not a list
```
**Output:** `{"key": "- not a list"}`

**In a list item's inline value**, however, a leading `-` (or `key:`)
recurses structurally, because a list item's inline `value` slot (§4.1)
re-enters `structure`. This is how compact single-line nesting is
written:

```syml
- - x
```
**Output:** `[["x"]]`

```syml
- name: Alice
  role: admin
```
**Output:** `[{"name": "Alice", "role": "admin"}]`

A string that would itself match `list_item`, `key_value`, or `section`
therefore has no encoding as a list item's inline value, and `dumps`
MUST raise for it there (§11.2.1 rule B); the same string is written
literally as a mapping's inline value. A root scalar is parsed
structurally line by line as well; see §11.2.1 for the strings `dumps`
cannot emit at each position.

### 7.3 Section Headers (Keys Without Values)

A key followed by a colon without an inline value creates a section. The value comes from nested content:

```syml
section:
  nested: content
```
**Output:** `{"section": {"nested": "content"}}`

A section with no nested content produces an empty string, whether followed by another element or EOF:

```syml
empty:
next: value
```
**Output:** `{"empty": "", "next": "value"}`

The same rule applies to a list item with no inline value and no nested
content (`-` alone, or `- ` per §9.3's zero-length-value normalization):
it evaluates to the empty string `""`.

### 7.4 Empty Documents

An empty document (or document with only comments/blank lines) produces an empty string (`""`).

### 7.5 Whitespace Handling

- Leading whitespace before content determines indentation level.
- The required whitespace after `:` (before an inline value) and after
  a list marker's `-` is one or more literal space characters (`ws` in
  §4.1); a tab does not satisfy this requirement. `key:\tvalue` and
  `-\tvalue` are therefore not recognized as a key-value pair or list
  item — each falls through to §7.6's literal-text rule (`"key:\tvalue"`,
  `"-\tvalue"` respectively), the same as any other unmatched structural
  line. This is the one rule that governs both separators: leading
  whitespace immediately after `:` or `-` is consumed by the required
  separator and is never part of the value; there is no separate
  "trimming" step.
- Trailing whitespace on a value is preserved as-is — it is never
  trimmed, because nothing after the value's content consumes it.
- A `-` forms a list marker only when followed by whitespace or end-of-line; otherwise the line is scalar text (§7.6).

> **Editor Compatibility Note:** Many text editors automatically strip trailing whitespace on save. This may inadvertently modify SYML values, and SYML has no quoting or escape syntax that could protect the whitespace. Authors who depend on trailing whitespace should configure their editors accordingly.

Quotation marks are ordinary value characters, and a value begins only
after the required separator space:

```syml
a: value
b: "value"
```
**Output:** `{"a": "value", "b": "\"value\""}` — `b`'s value is the seven
characters `"value"`, quotation marks included.

```syml
a: value
b: "value"
c:"value"
```
**Output:** `ERROR: OutOfContextNodeError` — `c:"value"` has no space
after the colon, so it is not a `key_value` but scalar text (§7.6), and
plain text at a mapping's own level has nowhere to attach (§6.4).

```syml
key:value
```
**Output:** `"key:value"` — no space before the value; the whole
line is scalar text (§7.6).

```syml
key:	v
```
**Output:** `"key:\tv"` — the tab immediately after `:` does not satisfy
the required separator whitespace; the whole line is scalar text (§7.6).

```syml
key: 	v
```
**Output:** `{"key": "\tv"}` — here the required separator IS a real
space (between `:` and the tab), so `key_value` matches; the tab is then
the first character of the inline value's content (§4.2 rule 3), not
part of the separator.

### 7.6 Lines That Resemble Structure

A line that does not match one of the structural forms is scalar text. SYML never
guesses at a malformed structure; it takes the line literally. This is a
deliberate consequence of the grammar in §4.1: when `list_item`, `key_value` and
`section` all fail to match, `line`'s `data` alternative succeeds and the line is
plain text.

This is why the `eol`/`&eol` guards in §4.1 matter. PEG ordered choice commits to the
first alternative that matches, so a structural rule that matched a *prefix* of
the line would strand the parser rather than fall through. `list_item` requires
whitespace or end-of-line after the `-`, and `section` requires end-of-line after
the `key:`, so neither can swallow a prefix of `-item` or `key:value` and then
fail. Both lines are rejected by every structural rule and reach `data` intact.

There is no exception for quotation marks. A value that begins with `'`
or `"` — at an inline position or on a bare line — is scalar text with
that character as its first character, since SYML has no quoted strings
(§4.1).

| Input | Result | Why |
|-------|--------|-----|
| `invalid key: value` | `"invalid key: value"` | Key pattern (§4.5) rejects the space |
| `Invalid: value` | `"Invalid: value"` | Key contains an uppercase letter (§4.5) |
| `key:value` | `"key:value"` | No whitespace after the colon (§7.5) |
| `-item` | `"-item"` | No whitespace after the list marker (§7.5) |
| `-42` | `"-42"` | Same rule; keeps negative numbers usable as scalars |
| `key: - not a list` | `{"key": "- not a list"}` | See §7.2 |
| `key:\tv` | `"key:\tv"` | Tab is not separator whitespace (§7.5) |
| `key: "a" trailing` | `{"key": "\"a\" trailing"}` | Quotation marks are ordinary value characters (§4.1) |
| `"unterminated` (root scalar) | `"\"unterminated"` | The leading `"` is ordinary text |

**Every line is lexed independently (§5.1 rule 6), regardless of what it
looks like in context.** A continuation-position line whose text before
its first colon is not a valid key (§4.5) — because it contains
whitespace, or an uppercase letter — cannot lex as `key_value`, so it
falls through to `data` and joins as literal prose:

```syml
a: Note
  Big Warning: do not touch
```
**Output:** `{"a": "Note\nBig Warning: do not touch"}` — `Big Warning`
contains a space, so it is not a valid key; the whole line joins `a`'s
multiline value as prose text.

```syml
a: Note
  Warning: do not touch
```
**Output:** `{"a": "Note\nWarning: do not touch"}` — `Warning` contains
an uppercase letter, so it is not a valid key either (§4.5); the line
joins as prose.

But if the same continuation-position text before the colon *is* a valid
key, the line lexes as `key_value` regardless of how it reads as prose,
and — since `a`'s KeyValue is already closed by its inline value — it
has nowhere to attach:

```syml
a: Note
  warning: do not touch
```
**Output:** `ERROR: OutOfContextNodeError` — `warning` has no whitespace
and no uppercase letter, so it is a valid key; the line is offered as a
child KeyValue, not as continuation text, and `a`'s KeyValue cannot
accept it (§9.3).

Dialogue and prose therefore round-trip as written, quotation marks and
all, as long as no line starts with a lowercase word followed by `: `:

```syml
stranger:
  - "You're late," she said.
  - choice: "I got held up."
```
**Output:**
```json
{"stranger": ["\"You're late,\" she said.", {"choice": "\"I got held up.\""}]}
```

This is why colons are usable in prose at all: not because SYML detects
"this looks like prose," but because whether a given line is text or
structure is decided purely by whether its own text lexes as a key —
the §4.5 pattern plus the no-uppercase rule — independently of
everything around it.

---

## 8. Error Conditions

Implementations MUST raise parse errors for:

### 8.1 Inconsistent Indentation

When a line's indentation doesn't fit the current structure — it is
neither a valid child (strictly greater than its containing key-value
pair or list item's level) nor equal to any real sibling's level, all the
way up to the document root — implementations MUST raise
`OutOfContextNodeError` (§9.2, §9.3). There is no separate exception
class for this case; see §8.2.

```syml
parent:
  child1: value
 child2: value
```
**Output:** `ERROR: OutOfContextNodeError` — `child2`'s indentation (1
space) is less than its sibling `child1`'s (2 spaces) but does not match
`parent`'s own level (0) either.

### 8.2 Context Violations

When structure types are mixed inappropriately, or a node cannot be
incorporated anywhere in the tree, implementations MUST raise the same
`OutOfContextNodeError` as §8.1 — both are "no place in the tree" for the
incoming line, and this specification does not distinguish them by
exception class:

```syml
- item1
- item2
key: value
```
**Output:** `ERROR: OutOfContextNodeError` — a mapping item cannot join a list context at the same level.

```syml
key1: value1
key2: value2
- item
```
**Output:** `ERROR: OutOfContextNodeError` — a list item cannot join a mapping context at the same level.

### 8.3 Duplicate Keys

Two keys are considered "the same key" if and only if they are equal as
sequences of Unicode code points (ordinal/code-point equality). Keys are
compared with NO Unicode normalization (NFC/NFD/NFKC/NFKD are all treated
as distinct unless already code-point-identical) and with NO case
folding (a key never contains an uppercase or titlecase letter, §4.5, but
lowercase letters with distinct code points, such as `ı` and `i`, are
distinct). Implementations MUST NOT apply locale-, platform-, or
collation-aware comparison.

When the same key (by this definition) appears multiple times in a
mapping, implementations MUST raise `DuplicateKeyError` (§11.3):

```syml
key: value1
key: value2
```
**Output:** `ERROR: DuplicateKeyError: Duplicate key 'key'`

Keys must be unique within their immediate mapping. The same key may
appear in different nested mappings. Detection happens at
tree-incorporation time (§9.3), before the mapping is materialized in
either data or source mode (§10.3) — mapping construction MUST NOT be
relied on to catch this, since two colliding keys would otherwise
collapse silently.

### 8.4 Tabs in Indentation

A tab character (U+0009) appearing in a line's leading indentation is a
parse error. This is detected by §9.0's pre-processing scan, before
§4.1's grammar runs, and MUST raise `TabIndentationError` (§11.3):

```syml
	key: value
```
**Output:** `ERROR: TabIndentationError`

Tabs are permitted inside inline value text, after the first non-tab
content on the line (§4.2 rule 3). A tab immediately after a list
marker's `-` or a key's `:` is not leading indentation and is not this
error — it fails to satisfy the required separator whitespace (§7.5) and
the line is read as scalar text instead (§7.6); it does not raise.

### 8.5 Document Limits

Implementations SHOULD enforce the recommended limits in §13.4 (maximum
nesting depth, line length, and document size) and raise
`DocumentLimitError` (§11.3) when a document exceeds them, rather than
crash or hang. For example, a document nested 501 levels deep — one past
the recommended default of 500 — SHOULD raise `DocumentLimitError` rather
than exhaust the host language's call stack.

---

## 9. Parsing Algorithm

**Level:** The indentation level of a node, defined as the column index (0-indexed) where the node's structural marker (`-` for list items, key name for mappings) or content begins.

### 9.0 Pre-Processing

Before tokenization (§9.1 step 2), a conforming implementation MUST, in
order:

1. Strip exactly one leading U+FEFF (BOM) if the document's first
   character is U+FEFF. A second U+FEFF immediately following it, or a
   U+FEFF anywhere else in the document, is ordinary content and MUST
   NOT be stripped or treated specially. A document that consists of a
   leading BOM and nothing else, once the BOM is stripped, is the empty
   document defined in §7.4 and yields `""`.
2. Normalize line endings by replacing every `\r\n` and every remaining
   bare `\r` with `\n` (§4.7) — normalization happens on the raw
   document text, before any grammar rule sees it, so no value ever
   contains a CR.
3. For each line, compute its **leading whitespace**: the maximal run of
   U+0020 (space) and U+0009 (tab) characters, in any mixture, starting
   at the beginning of the line. If nothing follows that run before the
   next line boundary (or the end of the document), the line is **blank**
   (§4.4) — skip the tab check for it entirely, even if its leading
   whitespace contains a tab. Otherwise (the line has non-whitespace
   content), if that leading-whitespace run contains a tab anywhere,
   raise `TabIndentationError` (§8.4, §11.3) — before §4.1's grammar is
   invoked for that line. This applies uniformly to every physical line,
   including one that will end up serving as a continuation line; there
   is no special case for "the tab is really the first character of the
   continuation's content" — a tab in the leading-whitespace run is
   always this error.

All three steps operate on the raw character stream and MUST complete
before §4.1's grammar or §9.2's incorporation algorithm processes any
line.

### 9.1 High-Level Process

1. **Pre-process**: Apply §9.0 (BOM stripping, line-ending normalization, tab-in-indentation scan)
2. **Tokenize**: Split document into lines
3. **Parse**: For each line, extract indent level and content, classifying
   it per §4.3/§4.4/§4.1. Each line is lexed independently of its
   position in the document (§5.1 rule 6) — the same physical line
   always classifies the same way, whether or not it happens to sit
   where a continuation was expected. A comment or blank line is never
   incorporated into the tree: it does not compete for `can_accept`,
   does not establish or affect any TextLeaf's baseline, and does not
   interrupt an in-progress multiline value (§5.1 rules 4-5). It is
   simply skipped, at any indentation level.
4. **Build Tree**: Incorporate nodes based on indentation
5. **Convert**: Transform tree to native data structures

### 9.2 Node Incorporation Algorithm

When incorporating a new node into the tree:

```
function incorporate_node(current_node, new_node):
    if current_node.can_accept(new_node):
        return current_node.add_child(new_node)
    else if current_node.has_parent():
        return incorporate_node(current_node.parent, new_node)
    else:
        raise OutOfContextNodeError
```

`add_child(new_node)` returns the TIP of the newly-added subtree:
`new_node` itself if it has no children, otherwise its deepest,
rightmost childless descendant. This is the node against which the
*next* line in the document is tested by `incorporate_node`.

An inline structural value (a `list_item` or `key_value` appearing as the
value of another `list_item` or `key_value`, e.g. `- key: v` or `- - x`)
is incorporated via this SAME algorithm, not attached directly as a child
of the immediately-enclosing node. This is required for §6.3-style deep
nesting to produce the documented output.

### 9.3 Node Acceptance Rules

**Empty**, for a ListItem or KeyValue, means "has no children." A
zero-length inline value (`- ` or `key: ` with nothing, or only
whitespace already consumed by the required `ws`, following) is
normalized to "no inline value at all" and does not create a child —
such a node remains empty. There is no way to write an explicit,
present empty inline value: `key: ""` is the two-character value `""`
(quotation marks are ordinary text, §4.1), a real child that closes the
node. Only spaces are consumed by `ws`: `key: \t` (space, then a tab)
has the one-character value `"\t"`, not an empty value. **Empty**, for a
List or Mapping, means "has no children" (this can only be observed
transiently during §9.4's automatic container creation).

```syml
key:
  nested: content
```
**Output:** `{"key": {"nested": "content"}}` — and the same output results
if the first line is written `key:` followed by one or more trailing
spaces (not shown literally here, since editors and pre-commit hooks
strip trailing whitespace; see §7.5's editor note). A trailing space after
`key:` does not create an empty-string value: `key:` and `key: ` behave
identically (§9.3's zero-length-value normalization), unlike `key: ""`,
which is the real, present two-character value `""` and would close the
node to further nesting.

| Current Node | Can Accept | Conditions |
|--------------|------------|------------|
| Root | Any | If empty, and new_node.level >= 0 |
| List | ListItem | If new_node.level == list.level |
| ListItem | Any | If empty, and new_node.level > item.level |
| Mapping | KeyValue | If new_node.level == mapping.level: accept if the key is not already present among mapping's children; if it is present, raise `DuplicateKeyError` immediately (§8.3) and do not fall through to §9.2's walk-up. If new_node.level != mapping.level: do not accept (walk up normally; no duplicate check is performed). |
| KeyValue | Any | If empty, and new_node.level > keyvalue.level |
| TextLeaf | TextLeaf | See below |

**TextLeaf's condition** (this implements §5.3): every TextLeaf tracks an
`anchor_level` (the level of the owning KeyValue/ListItem; −1 for a
scalar at the document root, which has no containing key/item) and a
`baseline`. How and when the baseline is fixed depends on how the
TextLeaf originated:

- If the TextLeaf holds an **inline** value (text on the same physical
  line as `key:`/`-`), its baseline starts unset. The first subsequent
  line accepted as a continuation of it — which must be strictly greater
  than `anchor_level` (§5.1 rule 1) — fixes the baseline to that
  candidate's own level.
- If the TextLeaf holds a **block** value (created when its first block
  line is incorporated into an empty KeyValue/ListItem, per the table
  above, which already enforces level > `anchor_level`) or is a **root
  scalar**, its baseline is fixed immediately at creation: to the block
  value's own first-line level, or unconditionally to `0` for a root
  scalar (regardless of that first line's own level).

Once the baseline is fixed (immediately for block/root, on the first
continuation for inline), a TextLeaf accepts a further candidate TextLeaf
if and only if the candidate's level is greater than or equal to the
baseline.

A continuation line is appended to the existing TextLeaf; it does not
create a new node, so the tip (§9.2) remains that TextLeaf and its parent
is the owning KeyValue/ListItem/Root. A candidate that fails this
condition (or, for an inline TextLeaf with no baseline yet, fails the
anchor condition) is not a continuation of this value. It is not simply
discarded: §9.2's ordinary walk-up re-offers it directly to the owning
container. This is what makes §5.3's "below baseline terminates the multiline value (line
belongs to parent/sibling context)" concrete: the terminating line
competes as an ordinary sibling or new child exactly as if the multiline
value had ended one line earlier, and may legitimately succeed (e.g. as
a dedented sibling key) or fail with `OutOfContextNodeError` (e.g. if no
ancestor's level matches it) like any other line. Because every line is
lexed independently (§5.1 rule 6), a candidate that lexes as a
`list_item`/`key_value`/`section` is never even offered to `TextLeaf.can_accept`
as a TextLeaf in the first place — it is a different node type, and
`TextLeaf` only ever accepts another `TextLeaf`.

A KeyValue or ListItem that already has a child (whether a TextLeaf
value or, transiently, during automatic container creation per §9.4) is
closed: `can_accept` returns false for it unconditionally, regardless of
the candidate node's type or level. A more-indented line that follows
such a node and does not qualify as a TextLeaf continuation under the
conditions above is therefore always a context violation (§8.2) once
combined with the `==`-sibling rule above, and MUST raise
`OutOfContextNodeError`.

There is no partial-indentation matching anywhere in this table: a
line's level must exactly equal an already-registered level somewhere in
the current ancestor chain (a List/Mapping's own level for a sibling, or
strictly greater than a KeyValue/ListItem's level for a child, or the
TextLeaf conditions above for a continuation). A level that fits none of
these relationships for any ancestor, all the way to Root, is a parse
error (§8.1/§9.2's `OutOfContextNodeError`). This — the `==` on List and
Mapping above, specifically — is also the enforcement mechanism for
§6.4's homogeneity rule: a List's acceptance test never accepts a
KeyValue (and a Mapping's never accepts a ListItem), so mixing structure
types at the same level always fails every acceptance test up the chain
and raises.

### 9.4 Automatic Container Creation

When a ListItem or KeyValue is incorporated into a container that doesn't have an appropriate parent:

1. Create the appropriate parent (List or Mapping)
2. Set parent's level to match the item
3. Incorporate parent into tree
4. Incorporate original item into new parent

---

## 10. Source Tracking (Optional Feature)

Implementations MAY provide source location tracking for parsed values.

### 10.1 Position Information

For each parsed value, track:
- **filename**: Source file path (if applicable)
- **start**: Starting position (line, column, character index)
- **end**: Ending position (line, column, character index)
- **text**: Original source text

### 10.2 Line/Column Numbering

- Lines are **1-indexed** (first line is line 1)
- Columns are **0-indexed** (first column is column 0)
- Character indices are **0-indexed** from start of document

> **Rationale:** This convention matches typical text editor displays, where the first line is shown as "Line 1" but cursor positions are often 0-indexed within lines.

### 10.3 Source-Preserving Mode

Implementations SHOULD offer two output modes:
- **Data mode**: Returns native strings (standard behavior)
- **Source mode**: Returns Source objects that stringify to their text but preserve location info

Source objects SHOULD be usable as dictionary keys interchangeably with
strings (i.e., `Source("foo") == "foo"` for equality and hashing).
Because Source objects compare and hash exactly as their text, an
implementation MUST NOT rely on final mapping construction to detect
duplicate keys (§8.3): two colliding Source keys collapse silently in a
dict/mapping comprehension just as two colliding plain-string keys
would. Duplicate-key detection MUST occur during tree incorporation
(§9.2-9.4), before the mapping is materialized in either data or source
mode.

---

## 11. API Reference

### 11.1 Required Functions

```
loads(document: string, filename?: string) -> any
    Parse a SYML string and return native data structures.

    Parameters:
        document: SYML document as string
        filename: Optional source filename for error messages

    Returns:
        - dict/map/object if document root is a mapping
        - list/array if document root is a list
        - string if document root is a scalar — this includes the empty
          string `""`, which is what `loads` returns for an empty
          document or a document containing only comments and/or blank
          lines (§7.4); these are not a separate return shape, only a
          scalar root whose value happens to be `""`.

load(file: file_object, filename?: string) -> any
    Parse SYML from a file object.

    Parameters:
        file: File-like object with read() method
        filename: Optional filename (defaults to file.name if available)

    `load()` MUST decode the file's bytes as strict UTF-8 (no `errors=`
    substitution, replacement, or permissive surrogate-escaping). A byte
    sequence that is not valid UTF-8 MUST raise a `ParseError` (or a
    clearly-documented decoding exception callers can distinguish from a
    successful parse) rather than being silently repaired into a string
    containing U+FFFD replacement characters or unpaired surrogates.

    Returns: Same as loads()
```

### 11.2 Optional Functions

```
parse(document: string, filename?: string) -> Node
    Parse and return the AST (abstract syntax tree).
    Allows access to source tracking and tree structure.

dumps(data: any) -> string
    Serialize native data structures to SYML format.
    (See §11.2.1-§11.2.3 for the normative rules a conforming
    implementation MUST follow; the reference implementation provides
    it.)

dump(data: any, file: file_object) -> None
    Serialize to SYML and write to file.
```

#### 11.2.1 Serialization Rules for Strings

SYML has no quoted strings, so a conforming `dumps` has exactly one way
to write each string: as the literal text on the page, such that
`loads(dumps(x)) == x`. The layout depends on the string and on its
position (a mapping value after `key:`, a list item value after `-`, or
the document root):

A. **Empty string.** Use the position's empty-value convention: nothing
   after `key:`, a bare `-`, or the empty document for a root scalar
   (§7.3, §7.4).
B. **Single-line value at a mapping or list position** (no `\n`). Write
   it inline, after `key: ` or `- `, exactly as is. It MUST NOT begin
   with a space or tab (the separator would absorb a space, §7.5, and a
   leading tab is unrepresentable, §4.2 rule 3). Trailing whitespace is
   preserved by `loads` and round-trips (§7.5). It is otherwise
   unrestricted at a mapping position: `{"k": "- x"}`, `{"k": "#x"}`,
   `{"k": "key: value"}`, and `{"k": "''"}` are all written literally,
   because `key_value`'s inline `data` never re-enters `structure`
   (§7.2). At a list position it MUST NOT itself lex as `list_item`,
   `key_value`, or `section` (`- - x` would nest; `- key: v` would be a
   mapping; `- -` would be a nested empty item, §7.2); such a string is
   unrepresentable there, though `["#x"]` and `["'x"]` are fine.
C. **Multi-line value** (contains `\n`), or **any root scalar**. Write it
   in block form: `key:` or `-` on its own line, then each line of the
   value on its own physical line, indented two spaces past the key or
   marker; a root scalar is written as bare lines at column 0. Because
   §5.1/§5.3 preserve indentation beyond the baseline, only the *first*
   line's leading whitespace is restricted: it MUST NOT begin with a
   space or tab (at a key or list position a leading space would move
   the baseline; at every position a leading tab is a tab in indentation,
   §8.4); later lines keep their own leading spaces. Every line of a
   block value MUST survive
   being lexed on its own (§5.1 rule 6), so the value is unrepresentable
   if any of its lines: is blank or whitespace-only (§5.1 rule 5);
   begins with a tab after any leading spaces (§9.0 step 3); begins with
   `#` or `//` after any leading spaces (§5.1 rule 4); or lexes as
   `list_item`, `key_value`, or `section` after any leading spaces,
   honouring §4.5's no-uppercase rule (`Listen: here` is text and
   round-trips; `listen: here` is structure and does not).
D. **Control characters.** A string containing `\r` (§4.7), NUL, or any
   other control character except LF and TAB (§4.6.1) is unrepresentable
   at every position: there is no escape sequence to write one. TAB is
   fine inside a value (`a\tb`) but not as a line's first character.
G. **Inline mapping in a list item** (`- key: v`): `dumps` MUST emit
   exactly one space between `-` and the key, so the key's column — and
   therefore the required column for any of its sibling keys (§6.2) —
   is deterministic. (Rules E and F of the draft, which governed quoted
   values, were retired with quoted strings; the letter G is kept so
   existing references stay valid.)

A conforming `dumps` MUST raise `UnrepresentableValueError` (§11.3) for
any string ruled unrepresentable above, rather than emit text that would
not read back as the same value. Such a string can often be carried at a
different position (a structure-shaped single line as a mapping value
rather than a list item), but a string containing a control character, a
blank line, or a comment-shaped or structure-shaped line inside a
multi-line value has no SYML encoding at all in this version.

#### 11.2.2 Unrepresentable Values: Empty Containers

The empty list and the empty mapping have no SYML encoding in this
version (v1.1 is a consistency release — see §14 — and adds no new
syntax). A conforming `dumps` MUST raise `UnrepresentableValueError`
(§11.3) when asked to serialize a structure containing an empty list or
empty mapping at any depth, rather than silently substituting an empty
string or omitting the key that held it.

**v1.2 candidate:** reserve the literal tokens `[]` and `{}` as the
entire value at a `value`/`data` position, denoting an empty list and
empty mapping respectively, without introducing general flow-collection
syntax. Trade-offs: closes this gap and matches JSON/YAML reader
expectations, but makes a *string* whose value is literally `[]` or `{}`
unrepresentable (there is no quoting to disambiguate it), and risks
scope creep toward general flow collections, which §1.2 rejects for SYML.

#### 11.2.3 Keys With No Encoding

A key containing whitespace, `:`, a control character, or an uppercase
or titlecase letter (§4.5's no-uppercase rule: `Name` would read back as
the text `Name: ...`), the empty-string key, or a key beginning with `#`
or `//` cannot be represented in this version — there is no quoted-key
syntax, and a leading `#`/`//` is always read as a comment regardless of
what follows (§4.5). A conforming `dumps` MUST raise
`UnrepresentableValueError` (§11.3) rather than emit a key that would
not read back correctly.

**v1.2 candidate:** add a quoted-key form (`'key with spaces': value`)
to `key_colon`. This would need to explicitly except a line beginning
with a quote character from the `comment` rule's priority, or a key
like `'#tag'` would remain unrepresentable for the same reason unquoted
`#tag` is today.

### 11.3 Exceptions

```
ParseError(ValueError)
    Base exception for all parsing errors. Every subclass below carries:
        message: str     -- human-readable description
        position: Pos     -- line/column/index (§10.1-10.2)
        line_text: str    -- the offending source line

OutOfContextNodeError(ParseError)
    A node could not be incorporated anywhere in the tree: a context
    violation (§8.2) or an indentation that fits no valid sibling,
    child, or parent level (§8.1). This specification does not
    distinguish these two cases by exception class.

DuplicateKeyError(ParseError)
    A key was repeated within the same mapping (§8.3).
    Additional attributes: key: str, first_position: Pos

TabIndentationError(ParseError)
    A tab character appeared in leading indentation (§4.2 rule 2; §8.4).

DocumentLimitError(ParseError)
    A document exceeded a recommended implementation limit (§13.4).

UnrepresentableValueError(ValueError)
    Raised by `dumps`, not `loads`, when asked to serialize a value with
    no SYML encoding in this version (§11.2.1, §11.2.2, §11.2.3).
```

A conforming implementation MUST expose these exact class names (or
re-export them under these names), so that catching code is portable
across implementations.

---

## 12. Complete Examples

### 12.1 Configuration File

```syml
# Application configuration
database:
  host: localhost
  port: 5432
  name: myapp_production

logging:
  level: INFO
  handlers:
    - console
    - file

features:
  - authentication
  - caching
  - rate-limiting
```

**Output:**
```json
{
  "database": {
    "host": "localhost",
    "port": "5432",
    "name": "myapp_production"
  },
  "logging": {
    "level": "INFO",
    "handlers": ["console", "file"]
  },
  "features": ["authentication", "caching", "rate-limiting"]
}
```

### 12.2 Data with Multiline Values

```syml
users:
  - name: Alice
    bio: Software engineer with
      10 years of experience in
      distributed systems.
  - name: Bob
    bio: Product manager
```

**Output:**
```json
{
  "users": [
    {
      "name": "Alice",
      "bio": "Software engineer with\n10 years of experience in\ndistributed systems."
    },
    {
      "name": "Bob",
      "bio": "Product manager"
    }
  ]
}
```

### 12.3 All Value Types Are Strings

```syml
types_demo:
  boolean_true: true
  boolean_false: false
  integer: 42
  float: 3.14159
  negative: -100
  scientific: 1.5e10
  null_value: null
  tilde: ~
  empty:
  quoted: "still a string"
```

**Output:**
```json
{
  "types_demo": {
    "boolean_true": "true",
    "boolean_false": "false",
    "integer": "42",
    "float": "3.14159",
    "negative": "-100",
    "scientific": "1.5e10",
    "null_value": "null",
    "tilde": "~",
    "empty": "",
    "quoted": "\"still a string\""
  }
}
```

Note that the `quoted` value keeps its quotation marks — they are content, not syntax, since SYML has no quoted strings (§4.1). The `empty` key has an empty string value, not null.

---

## 13. Implementation Notes

### 13.1 Parser Technology

The Python implementation (§15) uses a PEG (Parsing Expression Grammar) parser via the Parsimonious library. Implementations may use:
- PEG parsers
- Recursive descent parsers
- Line-by-line state machine parsing
- Any suitable parsing approach

### 13.2 Performance Considerations

- Line splitting should be memoized for position calculations
- Indentation calculation is a leading-whitespace scan followed by the
  §4.2/§8.4 tab-rejection check (§9.0), O(n) per line. There is no tab
  *normalization* step: a tab anywhere in a line's leading indentation
  is a parse error (§8.4) and must never be expanded, substituted, or
  assigned a column width.
- Tree incorporation is O(depth) per node

### 13.3 Unicode Support

SYML documents MUST be valid UTF-8; there is no "platform-native
encoding" fallback (see §11.1's `load()` decoding rule). Implementations should:
- Accept any valid Unicode in keys and values
- Count columns by characters (code points), not bytes
- Treat a line boundary as exactly one U+000A (LF), and only after the
  §9.0 CR/CRLF normalization pass has run. No other Unicode line- or
  paragraph-separator code point (including U+000B, U+000C, U+0085,
  U+2028, U+2029, and U+001C-U+001E) terminates a line, anywhere in a
  document. Implementations MUST NOT use a
  general-purpose "split into lines" library routine (e.g. Python's
  `str.splitlines()`, which recognizes additional separators) for
  tokenization, position tracking, or error-message line numbering;
  splitting must be done on literal `\n` only, or line/column numbers
  will silently disagree with the grammar's own notion of a line.
- A UTF-8 BOM (U+FEFF) MUST be stripped silently if and only if it is
  the first character of the raw document (character index 0), before
  any other pre-processing (§9.0) or parsing occurs. Exactly one leading
  BOM is stripped; if a second U+FEFF immediately follows, it is
  ordinary content and MUST NOT also be stripped. A U+FEFF appearing
  anywhere else in the document — at the start of a non-initial line or
  elsewhere in value text — is ordinary Unicode content and MUST be
  preserved verbatim.

### 13.4 Recommended Implementation Limits

To prevent uncontrolled resource consumption on adversarial or
accidentally pathological input, implementations SHOULD enforce, and
cleanly reject with `DocumentLimitError` (§11.3) rather than crash or
hang on, at least:

- **Maximum nesting depth:** 500 levels of List/Mapping/ListItem/KeyValue
  nesting. Documents nested deeper than this SHOULD be rejected before
  recursive tree-building is attempted, not merely allowed to overflow
  the host language's call stack.
- **Maximum line length:** 1,048,576 characters (1 MiB) per line. Longer
  lines SHOULD be rejected outright rather than parsed at reduced
  performance. Since every value is literal text (§4.1), a line's
  lexing cost is linear in its length, but a list item's inline `value`
  re-enters `structure` (§7.2), so a long run of `- - - …` on one line
  recurses once per marker; implementations SHOULD bound that depth as
  part of the nesting limit above.
- **Maximum document size:** 10 MiB. Larger documents SHOULD be rejected
  before parsing begins (a size check against the raw input, prior to
  any grammar work) rather than partially parsed.

These are default SHOULD limits for out-of-the-box safety;
implementations MAY expose them as configurable and MAY choose different
defaults suited to their deployment, but MUST document whatever limits
they enforce (or that they enforce none) so callers can reason about
worst-case behavior on untrusted input.

---

## 14. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-09 | Initial specification formalizing SYML syntax, released as the conforming reference implementation. There are no quoted strings and no escape sequences: every value is the literal text on the page and a `'` or `"` is ordinary content at every position, as in 0.6.2 (D18, which supersedes the draft's inline-quoting rules D2, D3, and D17). A mapping key contains no uppercase or titlecase letter (Unicode General_Category `Lu`/`Lt`), so a line such as `Name: x` or `Listen: here` is text, not a mapping (D19; §4.1, §4.5 — breaking vs 0.6.2). Includes tabs-in-indentation error, duplicate key error, empty values produce empty strings, line ending normalization. Breaks compatibility with Python reference implementation v0.6.2. Clarifies that malformed structural lines parse as scalars rather than raising, and that whitespace after `:` is required before an inline value. §4.1 grammar corrected to load in Parsimonious and to consume line endings (fixes alternation stranding and `&eol`-only lines that stopped parsing after one line). New §9.0 pre-processing step formalizes BOM stripping, CRLF/CR normalization, and a leading-tab scan that raises `TabIndentationError`. §9.3 sibling acceptance changed from `>=` to `==` for List/Mapping, enforcing §4.2 rule 6 and §6.4's homogeneity rule. Duplicate-key detection added at incorporation time, raising `DuplicateKeyError`; key equality is code-point equality, with no Unicode normalization and no case folding (§8.3). §5.3's TextLeaf baseline/termination rules made concrete: the baseline is the level of the first line of the value that occupies a line of its own — for an inline value, its first continuation line; for a block value, its first block line (unlike the inline case, this sets the baseline immediately); for a root scalar, a fixed 0 — and a below-baseline line terminates the value and is re-offered to the owning container rather than silently joining or vanishing. Comment and blank/whitespace-only lines inside a continuation block are always skipped and never terminate or affect the baseline, and a value containing a literal blank line (a paragraph break) cannot be written at all and is unrepresentable by `dumps` (§5.1 rules 4-5, §11.2.1). §7.2 clarified: a mapping's inline value is always literal, but a list item's inline value is parsed structurally (`- - x` nests; `key: - x` does not), so a structure-shaped string is unrepresentable by `dumps` at a list position; a root scalar is parsed structurally line by line and is always written in block form (§11.2.1). Every physical line is now lexed independently of its position in the document: a continuation-position line that itself lexes as `key_value`/`list_item`/`section` is that structure, not literal text, and — once its owning node is closed — raises `OutOfContextNodeError`; plain text at a container's own level (alongside sibling key-value pairs) is likewise an error (§5.1 rule 6, §6.4, §7.6). A key written inline after a list marker (`- name: v`) sets its sibling column to the key's own column, not the marker's, regardless of spacing after `-` (§6.2); `dumps` MUST emit exactly one space after `-` for this reason (§11.2.1 rule G). The key pattern's `\s` is now defined as exactly the Unicode `White_Space` code points, not a host regex engine's default `\s` (§4.5). The formal grammar's top rule is now `document = (line "\n")* line?` with `eol` as a lookahead-only rule anchored on absolute end-of-input, replacing the nullable-repetition-prone `lines = line*`/`~"$"` pair; there is no separate `blank` rule (§4.1, §4.4). Every example in §4.2 and §8.1-§8.5 had its trailing `# Level N`/`# ERROR: ...` annotation removed in favor of prose or an **Output:** line, since those annotations were themselves invalid SYML content that would otherwise become part of the parsed value. §4.5: a key may not begin with `#` or `//` (the comment rule makes it unreachable); keys with whitespace, a colon, an uppercase or titlecase letter, or no encoding are documented as unrepresentable (§11.2.3). §3.3: mapping insertion order is now a MUST, replacing the earlier disclaimer that consumers must not depend on it. A zero-length inline value (`key: `, `- `) is now normalized to the same as no value at all (`key:`, `-`); `key: ""` is the two-character value `""` (§9.3). §7.3's empty-value rule extended explicitly to list items. §11.1 clarifies that an empty or comment-only document is the scalar case (`""`), not a fourth return shape; `load()` now MUST decode strictly as UTF-8, raising rather than silently repairing invalid bytes. New §11.2.1-§11.2.3 give `dumps` normative serialization rules — a single-line string is written inline, a multi-line string or any root scalar in block form, and a string with no literal encoding (a control character other than LF/TAB, a leading space or tab, a blank, tab-initial, comment-shaped, or structure-shaped line in block form, or a structure-shaped list item value) is `UnrepresentableValueError` — and require `UnrepresentableValueError` for empty containers and keys with no encoding. §11.3's exception list expanded to `DuplicateKeyError`, `TabIndentationError`, `DocumentLimitError`, and `UnrepresentableValueError`; there is no `InconsistentIndentationError` — §8.1 and §8.2 both raise `OutOfContextNodeError`. §13.2's tab bullet corrected: there is no tab normalization, only rejection. §13.3 defines a line boundary as exactly one LF (not the general Unicode line-separator set a naive `splitlines()` would use) and fully specifies BOM scope (index 0 only, exactly one, ordinary content everywhere else). New §13.4 recommends default limits (500 levels of nesting, 1 MiB lines, 10 MiB documents). New §4.6.1 states that control characters other than LF, including NUL, are permitted verbatim in values. §9.2 specifies that `add_child` returns the tip of the added subtree and that inline structural values (`- key: v`, `- - x`) are incorporated through the same algorithm. §11.3: `ParseError` derives from the host's `ValueError`-equivalent, `UnrepresentableValueError` is a `ValueError` raised by `dumps`, and the exception class names are normative. Header status line now names `syml` 1.0.0 as the conforming reference implementation. |

---

## 15. Python Implementation

A Python implementation is available at: https://github.com/eykd/syml. As of
v1.0.0, it is the conforming reference implementation of this specification
(see the status line at the top of this document and §14).

Licensed under MIT License.

```
pip install syml
```

```python
import syml

data = syml.loads("""
name: SYML
type: markup language
features:
  - simple
  - predictable
  - string-only values
""")

print(data)
# {'name': 'SYML', 'type': 'markup language',
#  'features': ['simple', 'predictable', 'string-only values']}
```
