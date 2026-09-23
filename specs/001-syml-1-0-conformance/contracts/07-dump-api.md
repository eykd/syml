# Contract 07 — `dumps` and `dump` (§11.2)

**Requirements**: FR-011 | **User story**: US7
**Spec**: §11.2, §11.2.1–§11.2.4, §7.2, §6.2 | **Decisions**: D1, D8, D17
**Audit gap**: 17 | **Research**: R-06 (format choices)

> No fenced example below carries a literal trailing space; `␠` marks one.

## Surface

```python
# src/syml/serializer.py, re-exported from syml/__init__.py

def dumps(data: SymlInput) -> str:
    """Serialize to SYML text, so that loads(dumps(x)) == x.

    Raises UnrepresentableValueError for a SYML value with no encoding
    (§11.2.2-.4) and TypeError for anything that is not str, list, or dict,
    including a non-str mapping key.

    Output format (an implementation choice, not conformance): two-space
    indentation, no blank lines, exactly one trailing newline, keys in
    insertion order. The empty string serializes to the empty document ''.
    When quoting is required, single quotes are preferred. At a list-item
    position, a quoted value that would re-read as a mapping is written
    double-quoted with every ':' escaped as \\u003a. If the output would
    begin with U+FEFF, one extra U+FEFF is prepended, because loads strips
    exactly one leading mark."""

def dump(data: SymlInput, file_obj: IO[str]) -> None:
    """Serialize with dumps, then write the whole result in a single write()
    call. If dumps raises, nothing is written. SYML documents are UTF-8
    (§13.3): open the handle with encoding='utf-8'. dump writes through the
    handle's own codec and does not check it, so a locale-default handle
    can write bytes that are not UTF-8. A lone surrogate in any string is
    written literally (SYML has no escape for one); a strict UTF-8 stream
    then raises its own UnicodeEncodeError, not a SYML error. A file
    reopened with encoding='utf-8-sig' loses one leading U+FEFF to the
    codec and one to §9.0, so a value's own leading U+FEFF does not survive
    that round trip; writing with 'utf-8-sig' adds a mark instead."""
```

**The parameter type is `SymlInput`, not `SymlData` (red-team pass 20).**
`SymlData = str | list[SymlData] | dict[str, SymlData]` is the right
*return* type for `loads`, but `list` and `dict` are invariant, so as a
*parameter* type it rejects every typed caller: under mypy strict,
`dumps(cfg)` with `cfg: dict[str, str]` is an `arg-type` error, and so are
`list[str]` and `dict[str, list[str]]` (verified). Only a literal or a value
already typed `SymlData` would pass, which fails Principle II for the
serializer's whole audience. The parameter is therefore

```python
type SymlData = str | list[SymlData] | dict[str, SymlData]   # basetypes.py (PEP 695)
SymlInput = str | list[Any] | dict[str, Any]                  # basetypes.py, beside SymlData
```

**`SymlData` is a PEP 695 `type` statement (red-team pass 23).** Written as
a plain assignment, `SymlData = str | list[SymlData] | …` refers to itself
before it exists and raises `NameError` when `basetypes` is imported. mypy
does not report it (it passes the file); ruff reports `F821` (both
verified). The `type` form is recursive by construction, passes mypy 1.20
and ruff under this repo's settings, and a `SymlData` value is still
accepted where `SymlInput` is expected (verified). String forward
references (`list['SymlData']`) also work; the `type` form is the one the
py312 target and ruff's `UP040` point to.

which accepts those three (and `loads`'s own `SymlData`), and still rejects
`dict[int, str]` and a tuple at the top level, matching the runtime type
table below. Below the top level `Any` defers to the runtime check, which
raises `TypeError` for anything that is not `str`, `list`, or `dict`. Both
aliases live in `basetypes.py` (plan.md § Project Structure) because
`serializer.py` precedes `__init__.py` in the import order.

The two docstrings in § Surface are the text the rest of this contract points at
("documented in the `dumps` docstring"). The doubled backslash in `\\u003a`
is deliberate: in a non-raw docstring a single one would be decoded to `:`. Each sentence is covered by a section
below (red-team pass 16 wrote them out in full).

**`dump` serializes before it writes (red-team pass 16).** A streaming `dump`
that writes line by line would, on `dump({'a': '1', 'b': {}}, fp)`, write
`a: 1` and then raise on the empty mapping. A caller who catches the error
is left with a file that loads, with no error, as `{'a': '1'}`. So `dump` is
`file_obj.write(dumps(data))`, and an `UnrepresentableValueError` or
`TypeError` leaves the stream untouched. Whether the *file* survives is the
caller's business (`open(p, 'w')` has already truncated it).

`dump` takes a **text** stream only. The asymmetry with `load` (which takes both)
is deliberate: `load`'s widening answers an installed base of `open(p, 'rb')`
callers; there is no equivalent argument in the write direction, and
`TextIOWrapper` is one line away (R-06).

### The output handle's codec (red-team pass 20)

§13.3 says SYML documents MUST be valid UTF-8. `dump` produces a `str` and
the **handle** encodes it, so which bytes reach the file is the handle's
codec and error handler, not `dump`'s. Verified with `io.TextIOWrapper`
over `io.BytesIO`:

| Handle | Value | Bytes written | Then |
| --- | --- | --- | --- |
| `encoding='utf-8'` | `{'k': 'é'}` | `k: \xc3\xa9\n` | every `load` path round-trips |
| `encoding='cp1252'` (also `open(p, 'w')` under a cp1252 locale, the Windows default before Python 3.15) | `{'k': 'é'}` | `k: \xe9\n` — not UTF-8 | `load(open(p, 'rb'))` raises `EncodingError`; only a cp1252 text handle reads it back |
| `encoding='cp1252'` | `{'k': '☺'}` | nothing: `UnicodeEncodeError` from `write`, underlying buffer still `b''` | the single-write rule holds on the codec path too |
| `encoding='utf-8', errors='surrogateescape'` | `{'k': 'a\udc80'}` | `k: a\x80\n` — not UTF-8 | `load(open(p, 'rb'))` raises `EncodingError` |
| `encoding='utf-8-sig'` | `'\ufeffx'` | `\xef\xbb\xbf` three times, then `x\n` | a binary `load` returns `'\ufeff\ufeffx'`; only a `utf-8-sig` reader gets `'\ufeffx'` back |
| default `newline=None` on Windows | any | `\n` written as `\r\n` | harmless: §9.0 normalizes it, and rule C escapes every `\r`/`\n` inside a value, so no literal break is ever translated |

So `dump`'s docstring tells the caller to open the handle with
`encoding='utf-8'`, and the round-trip obligation below uses exactly that.
Every row above is a caller's codec choice, the same class as Contract 06's
text-handle rows and pass 15's `utf-8-sig` note, and is documented rather
than prevented.

**Considered and not adopted: raising on a non-UTF-8 `file_obj.encoding`.**
It would turn the cp1252 rows into a loud error before anything is written.
It was not adopted because `encoding` is not part of `IO[str]` (a `StringIO`
reports `None`, and a custom writer may have none or a free-form string), so
the check would police only some handles, and it would reject a console
`sys.stdout` even for ASCII output, whose bytes are UTF-8 under any
ASCII-compatible codec. Adding it after 1.0 would narrow what `dump`
accepts, so it is recorded here as a deliberate choice, not an oversight.

## Type contract

| Input | Outcome |
| --- | --- |
| `str`, `list`, `dict` (recursively) | serialized |
| `int`, `float`, `bool`, `None`, anything else | `TypeError` |
| a mapping key that is not a `str` (`{1: 'v'}`, `{None: 'v'}`, `{b'k': 'v'}`) | `TypeError`, raised by an explicit `isinstance(k, str)` check **before** `key_is_representable` (pass 16) |

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
   text. Nothing else is escaped. In particular a lone surrogate (a `str` can
   hold one, and `loads` passes one through from a bare line) stays literal,
   because a `\uD800`-style escape is a decode error (D3). `dump` to a UTF-8
   stream then raises the stream's own `UnicodeEncodeError`. That is the
   codec's behaviour, noted in the `dump` docstring, not a SYML rule.
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
| `a: b` as a mapping value | `k: a: b` (unaffected, and **unquoted**: rule D exempts a mapping's inline value and no other rule applies; `loads('k: a: b')` is `{'k': 'a: b'}`) |

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
- It also catches parsimonious's `ParseError` and treats it as **"does not
  match"**. `Expression.match` raises that exception whenever nothing matches
  at offset 0, which is every ordinary list item: `hello`, `#x`, `'a'`, and
  the empty string all raise it (verified). A probe that caught only
  `RecursionError` would let a third-party exception out of `dumps(['hello'])`
  (red-team pass 16). The probe, in full:

```python
def structure_matches(s: str) -> bool:
    """Rule D and §11.2.4(a): does any prefix of `s` lex as `structure`?"""
    try:
        GRAMMAR['structure'].match(s)            # prefix match, stranded or not
    except RecursionError:
        return True                              # only a `- `-led string gets this deep
    except parsimonious.exceptions.ParseError:
        return False                             # nothing matched at offset 0
    return True
```

  The step-1 re-lex, `GRAMMAR['line'].match('- ' + rendered)`, needs neither
  catch. `line` always matches, because `data` matches the empty string, and
  a quoted rendering fails `structure` at its first character, so it is
  shallow.
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

**The test is the grammar, not the list (red-team pass 14).** §11.2.3's list
omits the C0/C1 controls that `key`'s class also excludes (§4.5). Read
literally, it lets `dumps({'a\x01b': 'v'})` emit `a\x01b: v`, which `loads`
reads back as the root scalar `'a\x01b: v'`. So the check is one probe:

```python
def key_is_representable(k: str) -> bool:
    try:
        m = GRAMMAR['key'].match(k)        # prefix match, like rule D's probe
    except parsimonious.exceptions.ParseError:
        return False                       # nothing matched: '' or a leading excluded char
    return m.end == len(k) and not k.startswith(('#', '//'))
```

The empty key fails the match, since `key` is `+`. Whitespace, `:`, C0, C1,
U+00A0, U+2028, and the rest of D15's set all stop the match short. The
enumeration therefore cannot drift from §4.5, and U+001C–U+001F are decided
the same way under either reading of "whitespace" (R-01). The parsimonious
`ParseError` from a zero-length match is caught **inside** this function.
`dumps` has no visitor, so nothing wraps it, but it must not escape `dumps`
(FR-009's spirit, and it is not `UnrepresentableValueError`).

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
`dumps('')` is `''`, with no trailing newline. It is the one output the
"exactly one trailing newline" format choice does not apply to (pass 16).
`'\n'` would also load as `""`, but it is a one-blank-line document, not the
empty one.

### A leading U+FEFF (red-team pass 14)

§9.0 step 1 strips one U+FEFF at index 0, so a document whose **first
character** is U+FEFF loses it on reload: `dumps('\ufeffx')` and
`dumps({'\ufeffk': 'v'})` would read back as `'x'` and `{'k': 'v'}`. No
§11.2.3/.4 condition covers either value. U+FEFF is not in D15's
`White_Space` set, is not a control character, and is admitted by `key`'s
class. Only the first character of the output is exposed. A root list starts
with `-`, and every later key follows a line break.

**Rule**: after rendering, if the output's first character is U+FEFF,
`dumps` prepends one U+FEFF. §9.0 strips exactly that one (Contract 01's
`"\ufeff\ufeffkey: v"` row), so the value's own mark survives, and idempotence holds
because `dumps` makes the same choice again. This is an output-format
choice, not a spec edit. Raising `UnrepresentableValueError` instead is
plan.md open item 5.

The prefix survives `dump` then `load` through a binary handle or a plain
UTF-8 text handle, because both hand `preprocess` both marks. A caller who
reopens the file with `encoding='utf-8-sig'` has the codec strip the first
mark and §9.0 strip the second, so the value's own mark is lost. That is the
caller's codec choice, noted in the `dump` docstring, not a rule `dumps` can
enforce (red-team pass 15).

| Value | Emitted |
| --- | --- |
| `'\ufeffx'` (root scalar) | `'\ufeff\ufeffx\n'` |
| `{'\ufeffk': 'v'}` | `'\ufeff\ufeffk: v\n'` |
| `{'a': 'x', '\ufeffk': 'v'}` | `'a: x\n\ufeffk: v\n'` (not first; no prefix) |
| `{'k': '\ufeffv'}` | `'k: \ufeffv\n'` (not first; no prefix) |

D17 stands: no root-scalar quoting, no new grammar rule for the root position.
Such values are carried as a mapping or list value instead, where quoting is
available. (See research.md's carried-forward table.)

## Round-trip invariant (FR-011, SC-003)

```
loads(dumps(x)) == x     for every representable x
```

Every value outside the representable set raises `UnrepresentableValueError`
(or `TypeError` for a non-SYML type). US7.1 is a property over a corpus; plan
it as a Scenario Outline with a shared corpus, not as ten hand-written
rows.

**Where the corpus lives (pass 25).** A pytest fixture cannot be shared
here: US7's binding sits under `tests/acceptance/`, which the unit run
`--ignore`s, and `tests/test_serializer.py` cannot see a fixture defined in
that directory's `conftest.py`. The corpus is therefore a plain module,
`tests/serialization_corpus.py`, holding `CORPUS: dict[str, SymlInput]`
(identifier → value) and `UNREPRESENTABLE: dict[str, object]` (the raising
set, including the six keys named below). `tests/test_serializer.py`
parametrizes over every `CORPUS` entry, so an entry is never covered only by
acceptance. US7.1's `Examples:` rows name `CORPUS` keys, and the binding
indexes `CORPUS[corpus_id]`, so a stale identifier fails with `KeyError`
instead of passing. The module is not collected (its name does not start
with `test_`) and is inside the mypy file set.

**Corpus must include**: the empty string; strings with leading/trailing space
and tab; strings containing `\n`, `\r`, NUL, and other C0 controls; strings
that look like structure (`key: v`, `- x`, `-42`, `key:value`); strings
beginning with `'`, `"`, `#`, `//`; the literals `''` and `""`; backslash
with colons at a list-item position (`a\: b`, the literal text `\u003a`,
`a: 'b" \c`); stranding structure-shaped strings (`k: "a" x`, `k: 'v' x`);
`'- ' * 200 + 'x'` as a list item, a mapping value, and a root scalar (the
last raises `UnrepresentableValueError`, never `RecursionError`); astral-plane
and combining characters; nested mappings and lists to depth 4; a list of
mappings (rule G); insertion-ordered mappings with non-sorted keys (US7.5);
a root scalar `'\ufeffx'` and a first key `'\ufeffk'`, each round-tripping
through the protective U+FEFF (pass 14). Keys `a\x01b`, `a\x7fb`,
`a\x9fb`, `a\x1cb`, `a\xa0b`, and `a\u2028b` are in the **raising** set, not
the corpus.

`dump(x, fp)` then `load(fp)` equals `x` (US7.9), for `fp` a `StringIO` or a
handle opened with `encoding='utf-8'`, rewound between the two calls
(§ The output handle's codec).

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
- Every row of the list-item table above, asserted on `dumps` output
  (pass 25: the mapping-value row read `k: 'a: b'` until then, which
  contradicts rule D's exemption and fails against a correct `dumps`).
- `dumps(['- ' * 200 + 'x'])` round-trips and `dumps('- ' * 200 + 'x')` raises
  `UnrepresentableValueError`; neither raises `RecursionError`.
- `dumps(5)` → `TypeError`, not `UnrepresentableValueError`.
- These runtime `TypeError` calls are mypy errors in the type-checked test
  module, so each carries a `# type: ignore[...]` with the code mypy
  reports: `arg-type` for `dumps(5)` and for a variable typed
  `dict[int, str]`, but `dict-item` for a literal such as `{1: 'v'}`
  (verified, pass 23). Under `warn_unused_ignores = true` those same
  ignores are the static half of the typing obligation below: if a later
  signature change starts accepting the call, the ignore goes unused and
  mypy fails.
- Non-`str` keys (`{1: 'v'}`, `{None: 'v'}`, `{True: 'v'}`, `{b'k': 'v'}`,
  `{('a',): 'v'}`) → `TypeError` raised by `dumps` itself, not by `re`.
- `structure_matches` returns `False` for `hello`, `#x`, `'a'`, `''`, and
  `True` for `a: b`, `k:`, `-`, `k: "a" x`, and `'- ' * 200 + 'x'`.
  `dumps(['hello', '#x', 'plain text'])` raises nothing from
  `parsimonious.exceptions`. That package is never seen by a `dumps` caller,
  for any value, not only for keys.
- `dumps('') == ''`.
- `dump` over a `StringIO` with `{'a': '1', 'b': {}}` raises
  `UnrepresentableValueError` and leaves `getvalue() == ''`.
- Typing (pass 20): mypy strict accepts `dumps(cfg)` for `cfg: dict[str,
  str]`, `list[str]`, `dict[str, list[str]]`, and `loads(...)`'s own
  `SymlData`, all without a cast, and rejects `dict[int, str]`. The test
  module itself is in the mypy file set, so these are ordinary typed calls.
- Codec (pass 20): `dump` of a non-ASCII value (`{'k': 'é'}`) to
  `io.TextIOWrapper(buf, encoding='utf-8')`, then `load(io.BytesIO(buf.getvalue()))`,
  round-trips. `dump({'k': '☺'}, TextIOWrapper(buf, encoding='cp1252'))`
  raises `UnicodeEncodeError` and `buf.getvalue() == b''` after `flush()`.
- `key_is_representable` against the six control/space keys above (all
  `False`), `''` (`False`), `'#k'` and `'//k'` (`False`), and `'k'`,
  `'emoji🎉key'`, `"'a"` (all `True`). No parsimonious exception leaves
  `dumps` for any key.
- Leading U+FEFF: the four rows of § A leading U+FEFF, each asserted on
  `dumps` output **and** through `loads(dumps(x)) == x`.
- Idempotence over the corpus.
- Format choices asserted against a golden fixture, labelled in the test name as
  an implementation choice, not conformance.
