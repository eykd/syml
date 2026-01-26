# SYML Specification

**Version:** 1.0
**Status:** Reference Implementation in Python (v0.6.2)

---

## 1. Introduction

SYML (Simple YAML-like Markup Language) is a lightweight, structured document markup language with YAML-like syntax but fundamentally simpler semantics. SYML deliberately avoids YAML's complexity and type coercion features in favor of predictable, string-only leaf values.

### 1.1 Design Philosophy

1. **All leaf values are strings** - No automatic type conversion (integers, floats, booleans, dates, etc.)
2. **Indentation-based structure** - Nesting is determined by whitespace indentation
3. **Minimal features** - No anchors, aliases, tags, or complex constructs
4. **Predictable parsing** - Same input always produces same output
5. **Source preservation** - Full tracking of source locations for debugging

> **Note:** SYML supports quoted strings (`'...'` and `"..."`) for whitespace preservation and escape sequences, a modest extension that maintains simplicity while enabling common use cases.

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

Mappings are unordered collections of key-value pairs, where keys are separated from values by a colon (`:`) followed by optional whitespace.

```syml
name: Alice
age: 30
city: Wonderland
```

**Output:** `{"name": "Alice", "age": "30", "city": "Wonderland"}`

> **Note:** Examples show keys in insertion order for readability; implementations may return keys in any order.

---

## 4. Syntax Rules

### 4.1 Formal Grammar (PEG Notation)

```peg
lines       = line*
line        = indent (comment / blank / structure / value) &eol
structure   = list_item / key_value / section

indent      = ~" *"              # Spaces only, no tabs

blank       = &eol
comment     = ~"(#|//+)+" text?

list_item   = "-" ws value

key_value   = section ws? quoted_value / section ws data
section     = key ":"
key         = ~"[^\s:\x00-\x1f\x7f-\x9f]+"   # Printable, non-whitespace, non-colon

eol         = "\n" / ~"$"
ws          = ~" +"              # Required whitespace (spaces)
text        = ~"[^\n]*"          # Any characters to end of line (including empty)

value       = structure / quoted_value / data
data        = text

# Quoted strings
quoted_value   = single_quoted / double_quoted
single_quoted  = "'" (~"''" "''" / ~"[^']")* "'"
double_quoted  = '"' (escape_seq / ~'[^"\\]')* '"'
escape_seq     = '\\' [\\"/nrt] / '\\u' [0-9a-fA-F]{4}
```

### 4.2 Indentation

Indentation determines the hierarchical structure of a SYML document.

**Rules:**
1. Indentation MUST use spaces only
2. Tab characters in indentation are a parse error
3. Tabs within values (after the initial content) are permitted
4. Indentation level = number of leading space characters
5. Child elements MUST have greater indentation than their parent
6. Sibling elements MUST have equal indentation

```syml
parent:           # Level 0
  child1: value1  # Level 2 (child of parent)
  child2: value2  # Level 2 (sibling of child1)
    grandchild:   # Level 4 (child of child2)
      value
```

**Invalid indentation (error):**
```syml
parent:
  child1: value
   child2: value   # ERROR: Inconsistent indentation (3 spaces)
```

### 4.3 Comments

Comments begin with `#` or `//` and continue to the end of the line.

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

### 4.4 Blank Lines

Blank lines (lines containing only whitespace) are ignored and do not affect document structure.

```syml
- item1

- item2


- item3
```
**Output:** `["item1", "item2", "item3"]`

### 4.5 Keys

Keys in mappings:
- MUST NOT contain whitespace characters
- MUST NOT contain colons (`:`)
- MUST NOT contain control characters (U+0000-U+001F, U+007F-U+009F)
- MAY contain any other printable Unicode characters (letters, numbers, punctuation, emoji)
- Pattern: `[^\s:\x00-\x1f\x7f-\x9f]+` (printable non-whitespace, non-colon)
- Keys MUST be unique within their mapping; duplicate keys are a parse error

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

# Block value
key:
  block value

# List with inline values
- inline item

# List with block values
-
  block item
```

### 4.7 Quoted Strings

SYML supports quoted strings for whitespace preservation and escape sequences.

#### Single-Quoted Strings (`'...'`)

Single-quoted strings are literal: no escape processing is performed.

- Content is taken literally, including backslashes
- To include a single quote within the string, use `''` (two single quotes)
- Leading and trailing whitespace inside the quotes is preserved

```syml
literal: 'hello\nworld'
with_quote: 'it''s fine'
padded: '  spaces  '
```

**Output:**
```json
{
  "literal": "hello\\nworld",
  "with_quote": "it's fine",
  "padded": "  spaces  "
}
```

#### Double-Quoted Strings (`"..."`)

Double-quoted strings support escape sequences:

| Escape | Result |
|--------|--------|
| `\\` | Backslash (`\`) |
| `\"` | Double quote (`"`) |
| `\n` | Newline (LF) |
| `\t` | Tab |
| `\r` | Carriage return (CR) |
| `\uXXXX` | Unicode code point (4 hex digits) |

```syml
escaped: "hello\nworld"
with_quote: "she said \"hi\""
unicode: "smiley: \u263A"
```

**Output:**
```json
{
  "escaped": "hello\nworld",
  "with_quote": "she said \"hi\"",
  "unicode": "smiley: ☺"
}
```

#### Whitespace in Quoted Strings

Quoted strings preserve leading and trailing whitespace that would otherwise be trimmed from unquoted values:

```syml
padded: "  hello  "
unquoted: hello
```

**Output:** `{"padded": "  hello  ", "unquoted": "hello"}`

### 4.8 Line Endings

Line endings are normalized during parsing:

- `\r\n` (CRLF, Windows) is converted to `\n` (LF)
- `\r` (CR, old Mac) is converted to `\n` (LF)
- Documents may end with or without a trailing newline

This ensures consistent behavior regardless of the source platform.

---

## 5. Multiline Values

When a scalar value spans multiple lines, continuation lines are joined with newline characters (`\n`).

### 5.1 Continuation Rules

1. Continuation lines MUST have greater indentation than the indentation level of the containing key-value pair or list item
2. The indentation reference point is the key or list marker, not the inline value
3. Multiple continuation lines are joined with `\n`

```syml
key: first line
  second line
  third line
```
**Output:** `{"key": "first line\nsecond line\nthird line"}`

In the above example, `key:` is at column 0, so continuation lines must be indented beyond column 0.

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

Relative indentation is preserved: common leading whitespace is stripped from continuation lines (similar to Python's `textwrap.dedent()`), with additional indentation beyond the first continuation line preserved.

```syml
key: line one
  line two
    line three (more indented)
```
**Output:** `{"key": "line one\nline two\n  line three (more indented)"}`

In this example, "line two" establishes the baseline indentation for continuations. "line three" has 2 additional spaces of indentation relative to "line two", which are preserved in the output.

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

**Invalid (mixing at same level):**
```syml
- list item
key: value     # ERROR: Cannot mix list items and key-values at same level
```

---

## 7. Edge Cases and Clarifications

### 7.1 Inline Colons in Values

After the first colon that separates key from value, additional colons are part of the value:

```syml
url: https://example.com:8080/path
```
**Output:** `{"url": "https://example.com:8080/path"}`

### 7.2 Inline List Syntax (Not Supported)

SYML does not support flow/inline collection syntax. List markers in values are literal text:

```syml
key: - not a list
```
**Output:** `{"key": "- not a list"}`

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

### 7.4 Empty Documents

An empty document (or document with only comments/blank lines) produces an empty string (`""`).

### 7.5 Whitespace Handling

- Leading whitespace before content determines indentation level
- Trailing whitespace on lines is preserved in values
- Whitespace between `-` and value is required (at least one space)
- Whitespace between `:` and an unquoted value is required
- Whitespace before a quoted value is optional

```syml
# Valid
key: value
key: "value"
key:"value"

# Invalid
key:value        # ERROR: No space before unquoted value
```

---

## 8. Error Conditions

Implementations MUST raise parse errors for:

### 8.1 Inconsistent Indentation

When a line's indentation doesn't fit the current structure:

```syml
parent:
  child1: value
 child2: value     # ERROR: Indentation less than sibling but not at parent level
```

### 8.2 Context Violations

When structure types are mixed inappropriately:

```syml
- item1
- item2
key: value         # ERROR: Cannot add mapping item to list context at same level
```

```syml
key1: value1
key2: value2
- item             # ERROR: Cannot add list item to mapping context at same level
```

### 8.3 Invalid Key Format

Keys containing whitespace or colons:

```syml
invalid key: value   # ERROR: Key contains whitespace
key:with:colons: v   # ERROR: Key contains colons (first colon ends key)
```

### 8.4 Duplicate Keys

When the same key appears multiple times in a mapping:

```syml
key: value1
key: value2     # ERROR: Duplicate key 'key'
```

Keys must be unique within their immediate mapping. The same key may appear in different nested mappings.

### 8.5 Tabs in Indentation

When tab characters are used for indentation:

```syml
	key: value    # ERROR: Tab character in indentation
```

Tabs are only permitted within values, not as leading indentation.

---

## 9. Parsing Algorithm

### 9.1 High-Level Process

1. **Tokenize**: Split document into lines
2. **Parse**: For each line, extract indent level and content
3. **Build Tree**: Incorporate nodes based on indentation
4. **Convert**: Transform tree to native data structures

### 9.2 Node Incorporation Algorithm

When incorporating a new node into the tree:

```
function incorporate_node(current_node, new_node):
    if current_node.can_accept(new_node):
        return current_node.add_child(new_node)
    else if current_node.has_parent():
        return incorporate_node(current_node.parent, new_node)
    else:
        raise OutOfContextError
```

### 9.3 Node Acceptance Rules

| Current Node | Can Accept | Conditions |
|--------------|------------|------------|
| Root | Any | If empty, and new_node.level >= 0 |
| List | ListItem | If new_node.level >= list.level |
| ListItem | Any | If empty, and new_node.level > item.level |
| Mapping | KeyValue | If new_node.level >= mapping.level |
| KeyValue | Any | If empty, and new_node.level > keyvalue.level |
| TextLeaf | TextLeaf | For multiline continuation |

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

### 10.3 Source-Preserving Mode

Implementations SHOULD offer two output modes:
- **Data mode**: Returns native strings (standard behavior)
- **Source mode**: Returns Source objects that stringify to their text but preserve location info

Source objects SHOULD be usable as dictionary keys interchangeably with strings (i.e., `Source("foo") == "foo"` for equality and hashing).

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
        - dict/map/object if document root is mapping
        - list/array if document root is list
        - string if document root is scalar
        - empty string if document is empty

load(file: file_object, filename?: string) -> any
    Parse SYML from a file object.

    Parameters:
        file: File-like object with read() method
        filename: Optional filename (defaults to file.name if available)

    Returns: Same as loads()
```

### 11.2 Optional Functions

```
parse(document: string, filename?: string) -> Node
    Parse and return the AST (abstract syntax tree).
    Allows access to source tracking and tree structure.

dumps(data: any) -> string
    Serialize native data structures to SYML format.
    (Not implemented in reference)

dump(data: any, file: file_object) -> None
    Serialize to SYML and write to file.
    (Not implemented in reference)
```

### 11.3 Exceptions

```
ParseError
    Base exception for all parsing errors.

OutOfContextNodeError(ParseError)
    Raised when a node cannot be incorporated due to
    indentation or context violations.

    Attributes:
        message: Error description
        position: Pos object with line/column info
        line_text: The problematic source line
```

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
    "quoted": "still a string"
  }
}
```

Note that the quoted value has its quotes stripped - they are syntax, not content. The `empty` key has an empty string value, not null.

---

## 13. Implementation Notes

### 13.1 Parser Technology

The reference implementation uses a PEG (Parsing Expression Grammar) parser via the Parsimonious library. Implementations may use:
- PEG parsers
- Recursive descent parsers
- Line-by-line state machine parsing
- Any suitable parsing approach

### 13.2 Performance Considerations

- Line splitting should be memoized for position calculations
- Indentation calculation (tab normalization) is O(n) per line
- Tree incorporation is O(depth) per node

### 13.3 Unicode Support

SYML documents are assumed to be valid UTF-8 (or platform-native encoding). Implementations should:
- Accept any valid Unicode in keys and values
- Count columns by characters (code points), not bytes
- Handle BOM (Byte Order Mark) if present

---

## 14. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01 | Initial specification based on Python reference implementation v0.6.2 |
| 1.0 | 2026-01 | Added quoted strings, tabs-in-indentation error, duplicate key error, empty values produce empty strings, line ending normalization, clarified continuation rules |

---

## 15. Reference Implementation

The reference implementation is available at: https://github.com/eykd/syml

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
