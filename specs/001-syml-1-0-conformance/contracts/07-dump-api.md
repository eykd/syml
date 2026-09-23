# Contract 07 — `dumps` and `dump` (§11.2)

**Requirements**: FR-011 | **User story**: US7
**Spec**: §11.2, §11.2.1–§11.2.4, §7.2, §6.2 | **Decisions**: D1, D8, D17
**Audit gap**: 17 | **Research**: R-06 (format choices)

> No fenced example below carries a literal trailing space; `␠` marks one.

## Surface

```python
# src/syml/serializer.py, re-exported from syml/__init__.py

def dumps(data: SymlData) -> str:
    """Serialize to SYML text. Raises UnrepresentableValueError, TypeError."""

def dump(data: SymlData, file_obj: IO[str]) -> None:
    """Serialize to SYML and write it to a text stream."""
```

`dump` takes a **text** stream only. The asymmetry with `load` (which takes both)
is deliberate: `load`'s widening answers an installed base of `open(p, 'rb')`
callers; there is no equivalent argument in the write direction, and
`TextIOWrapper` is one line away (R-06).

## Type contract

| Input | Outcome |
| --- | --- |
| `str`, `list`, `dict` (recursively) | serialized |
| `int`, `float`, `bool`, `None`, anything else | `TypeError` |

`UnrepresentableValueError` means "this *is* a SYML value, but it has no
encoding in this version". A non-string leaf is not a SYML value at all, so it
is a `TypeError`. R-06 records the alternative and why it was rejected.

## Quoting table (§11.2.1) — normative

A string MUST be quoted if any of:

| Rule | Condition |
| --- | --- |
| A | it is the empty string — use the position's empty-value convention (`key:`, `-`), **never** `''` or `""` |
| B | it has leading or trailing space or tab |
| C | it contains `\n`, `\r`, or any other control character |
| D | it is a **list item's** inline value and would itself match `list_item`, `key_value`, or `section` (a mapping's inline value is exempt — §7.2). "Would match" means `GRAMMAR['structure'].match(s)` succeeds — a **prefix** match, stranded or not: `k: "a" x` fails `parse` but must still be quoted (plan.md pass 4) |
| E | it is at an inline position and starts with `'` or `"` |
| F | it is exactly `''` or `""` |
| G | it is a list item's inline **mapping** value: emit exactly one space between `-` and the key |

**Rule C is a hard prohibition on block form**: `dumps` MUST NOT represent a
string containing `\n` via multiline block continuation. Use a double-quoted
string with `\n` escaped (US7.2).

**Single-quote preference**: when quoting is required and the value contains no
control characters, prefer `'...'` over `"..."`, to keep output literal per
§1.1 (US7.3).

**The one exception — quoted list items that would lex as mappings.** Under
§4.1 as printed, a list item's inline `value` tries `structure` before
`quoted_value`, and `key` admits `'` and `"`. So the rule-D-quoted rendering of
`a: b` at a list-item position, `- 'a: b'`, reads back as `[{"'a": "b'"}]`, and
`- "a: b"` fails the same way (plan.md § Edge Cases, pass 3). The mapping-value
position is not affected. The rule:

1. At a **list-item** inline position, **when one of rules B–F required
   quoting**, re-lex the chosen quoted rendering with
   `GRAMMAR['line'].match('- ' + rendered)`. An unquoted rendering, and rule
   A's bare `-`, are never re-lexed or re-quoted: `hello` stays `- hello` and
   the empty string stays `-`, never `- ""`.
2. If the result is anything other than a `list_item` whose value is one
   `quoted_value` spanning to end of line, emit the **double-quoted** form
   instead, with every `:` written as the four-hex-digit unicode escape
   `\u003a` (`escape_seq`'s `\uXXXX` alternative, Contract 02) rather than a
   literal `:` (and control characters escaped as rule C already requires).
   Escaping is **one pass per character** — `\` → `\\`, `"` → `\"`, `:` →
   `\u003a`, controls → their escapes. Substituting `:` first and escaping `\`
   afterwards turns the inserted escape into `\\u003a`, which loads as literal
   text.
   With no literal `:`, `key_colon` cannot match, and a value starting `"`
   cannot lex as a nested `list_item` or a comment, so the list item's value is
   a `quoted_value` by construction.

This is conformant as written: §11.2.1's single-quote rule is a preference and
its `loads(dumps(x)) == x` requirement is a MUST. It is documented in the
`dumps` docstring. Idempotence holds, because `loads` returns the plain `:` and
`dumps` makes the same choice again.

| Value at a list-item position | Emitted |
| --- | --- |
| `a: b` | `- "a\u003a b"` (single- and plain double-quoted forms both re-lex as a mapping, per steps 1–2 above) |
| `k:` | `- 'k:'` (rule D quotes it; the single-quoted form re-lexes as a quoted value) |
| `a:b` | `- a:b` (no rule requires quoting, so no re-lex) |
| `k: "a" x` | `- "k\u003a \"a\" x"` (rule D by prefix match; the single-quoted form strands) |
| `""` (empty) | `-` (rule A; never re-lexed) |
| `a: b` as a mapping value | `k: 'a: b'` (unaffected) |

## Format choices (R-06) — implementation, not spec

Documented in the `dumps` docstring and the README's serializer section, and
**not** asserted as conformance.

| Choice | Value |
| --- | --- |
| indent width | 2 spaces per level |
| blank lines between entries | none |
| trailing newline | exactly one |
| key order | insertion order (D8 — normative, not a choice) |
| mapping-valued key | `key:` + indented block |
| list-valued key | `key:` + indented `-` lines |
| list item holding a mapping | `- k: v`, siblings at the key's column |
| list item holding a list | `-` + indented `-` lines |

## Recursion in the rule-D and §11.2.4(a) probes

`structure` recurses in Parsimonious once per inline `- `, so lexing a raw
string such as `'- ' * 150 + 'x'` raises the host `RecursionError` (plan.md
pass 4). That string is representable — `- '- - … x'` loads, because a
quote-led line fails `structure` at its first character. So:

- The rule-D probe (and §11.2.4(a)'s, per line) catches `RecursionError` and
  treats it as **"matches `structure`"**. Only a `- `-led string can recurse
  that deep, so this is exact, not a guess.
- At a list-item position the value is then quoted; the quoted re-lex is
  shallow. At the root it is `UnrepresentableValueError` (condition a).
- The **probe** never lets `RecursionError` escape. This does not extend to
  `dumps`'s own traversal of deeply nested *data* (a naive recursive walk
  fails near 1,000 levels of nested lists): that is the same deferred §13.4
  depth limit as `loads`, and Contract 09 states it for both directions. A
  probe that hits the limit only because the data is already deep
  over-quotes a harmless list item, which is safe — quoting never breaks the
  round-trip — and never reaches the root position, which is not nested.

## Unrepresentable values

### §11.2.2 — empty containers (D1)

`UnrepresentableValueError` for an empty list or empty mapping **at any depth**
— never substitute `""`, never omit the key that held it (US7.6).

```python
dumps({"a": []})        # UnrepresentableValueError
dumps({"a": {"b": {}}}) # UnrepresentableValueError
dumps([])               # UnrepresentableValueError
```

### §11.2.3 — keys with no encoding (D1, M8)

`UnrepresentableValueError` for a key that contains whitespace or `:`, is the
empty string, or begins with `#` or `//` (US7.7). There is no quoted-key syntax
in v1.1 and a leading `#`/`//` is always a comment regardless of what follows
(§4.5).

### §11.2.4 — root scalars (D17)

`UnrepresentableValueError` for a root scalar that (US7.8):

| | Condition |
| --- | --- |
| a | would lex as `list_item`, `key_value`, or `section` on any of its lines |
| b | begins with `#` or `//` |
| c | contains `\n`, `\r`, or any other control character |
| d | has leading or trailing whitespace on any line |
| e | is exactly `''` or `""` |

The empty string **is** representable — as the empty document (§7.4).

D17 stands: no root-scalar quoting, no new grammar rule for the root position.
Such values are carried as a mapping or list value instead, where quoting is
available. (See research.md's carried-forward table.)

## Round-trip invariant (FR-011, SC-003)

```
loads(dumps(x)) == x     for every representable x
```

Every value outside the representable set raises `UnrepresentableValueError`
(or `TypeError` for a non-SYML type). US7.1 is a property over a corpus; plan
it as a Scenario Outline with a shared corpus fixture, not as ten hand-written
rows.

**Corpus must include**: the empty string; strings with leading/trailing space
and tab; strings containing `\n`, `\r`, NUL, and other C0 controls; strings
that look like structure (`key: v`, `- x`, `-42`, `key:value`); strings
beginning with `'`, `"`, `#`, `//`; the literals `''` and `""`; backslash
with colons at a list-item position (`a\: b`, the literal text `\u003a`,
`a: 'b" \c`); stranding structure-shaped strings (`k: "a" x`, `k: 'v' x`);
`'- ' * 200 + 'x'` as a list item, a mapping value, and a root scalar (the
last raises `UnrepresentableValueError`, never `RecursionError`); astral-plane
and combining characters; nested mappings and lists to depth 4; a list of
mappings (rule G); insertion-ordered mappings with non-sorted keys (US7.5).

`dump(x, fp)` then `load(fp)` equals `x` (US7.9).

**Idempotence**: `dumps(loads(dumps(x))) == dumps(x)`. This is why R-06 rejects
blank lines between top-level keys.

## Test obligations

- Every quoting-table rule, with a positive and a negative case.
- Every §11.2.2/.3/.4 condition raising.
- The round-trip property over the corpus above, with every `key: v`-shaped
  string placed **both** as a mapping value and as a list item (`["a: b"]`,
  `["': x"]`, `["k: 'v'"]`). Placing them only as mapping values would let the
  property pass while list items corrupt.
- A re-lex check: for every corpus string rendered at a list-item position,
  `GRAMMAR['line'].match('- ' + rendered)` is a `list_item` whose value is one
  `quoted_value` spanning to end of line, or an unquoted node named `text`
  (Contract 02's `data`/`text` alias — never a node named `data`) equal to the
  string.
- The re-lex runs only on quoted renderings: `dumps(["hello", ""])` is
  `- hello\n-\n`.
- `dumps(['- ' * 200 + 'x'])` round-trips and `dumps('- ' * 200 + 'x')` raises
  `UnrepresentableValueError`; neither raises `RecursionError`.
- `dumps(5)` → `TypeError`, not `UnrepresentableValueError`.
- Idempotence over the corpus.
- Format choices asserted against a golden fixture, labelled in the test name as
  an implementation choice, not conformance.
