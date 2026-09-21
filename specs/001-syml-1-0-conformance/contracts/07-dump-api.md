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
| D | it is a **list item's** inline value and would itself match `list_item`, `key_value`, or `section` (a mapping's inline value is exempt — §7.2) |
| E | it is at an inline position and starts with `'` or `"` |
| F | it is exactly `''` or `""` |
| G | it is a list item's inline **mapping** value: emit exactly one space between `-` and the key |

**Rule C is a hard prohibition on block form**: `dumps` MUST NOT represent a
string containing `\n` via multiline block continuation. Use a double-quoted
string with `\n` escaped (US7.2).

**Single-quote preference**: when quoting is required and the value contains no
control characters, prefer `'...'` over `"..."`, to keep output literal per
§1.1 (US7.3).

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
beginning with `'`, `"`, `#`, `//`; the literals `''` and `""`; astral-plane
and combining characters; nested mappings and lists to depth 4; a list of
mappings (rule G); insertion-ordered mappings with non-sorted keys (US7.5).

`dump(x, fp)` then `load(fp)` equals `x` (US7.9).

**Idempotence**: `dumps(loads(dumps(x))) == dumps(x)`. This is why R-06 rejects
blank lines between top-level keys.

## Test obligations

- Every quoting-table rule, with a positive and a negative case.
- Every §11.2.2/.3/.4 condition raising.
- The round-trip property over the corpus above.
- `dumps(5)` → `TypeError`, not `UnrepresentableValueError`.
- Idempotence over the corpus.
- Format choices asserted against a golden fixture, labelled in the test name as
  an implementation choice, not conformance.
