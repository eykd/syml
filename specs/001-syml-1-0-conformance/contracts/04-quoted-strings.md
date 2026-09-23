# Contract 04 — Quoted strings (§4.7) and the quote-guard rule (§4.1)

**Requirements**: FR-008 | **User story**: US6
**Spec**: §4.1 (quote-guard), §4.7, §7.5, §7.6, §8.5, §9.3
**Decisions**: D2, D3, D4 | **Audit gaps**: 1, 2 | **`todo.txt`**: A1 (its OPEN QUESTION is decided — do not re-litigate)

> No fenced example below carries a literal trailing space; `␠` marks one.

## Surface

```python
# src/syml/quoting.py  (new module)

def decode_single_quoted(raw: str) -> str:
    """Decode a '...' literal. '' is an embedded apostrophe. No escape processing."""

def decode_double_quoted(raw: str) -> str:
    """Decode a "..." literal per the §4.7 escape table.

    Only ever receives text the grammar matched, so every escape is
    syntactically valid; raises MalformedQuotedStringError (with .escape and
    .code_point) only for a code point above U+10FFFF or a surrogate.
    """

def diagnose_malformed(text: str) -> str | None:
    """The .escape for a quote-guard fallthrough: the first invalid or
    incomplete escape, or None if the value is merely unterminated.
    .code_point is always None on this path. See below."""
```

## Where quoting is recognized (D2)

**Only at an inline position**: immediately after `key:` (`key_value`'s first
alternative) or after a list marker (`list_item`'s inline `value`). Nowhere
else. A root scalar's lines, a block value's lines including its first, and any
continuation line never attempt to quote-decode; a leading `'` or `"` there is
ordinary text (§4.7, §7.6).

| Input | Result | Why |
| --- | --- | --- |
| `"unterminated` (root scalar) | `"\"unterminated"` | not an inline position — US6.9 |
| `key: He said\n  'yes'` | `{"key": "He said\n'yes'"}` | continuation line — US6.10 |
| `key: 'a'` | `{"key": "a"}` | inline |
| `- 'a'` | `["a"]` | inline |

## Single-quoted (`'...'`)

Literal: no escape processing, backslashes survive, `''` is one apostrophe,
interior whitespace preserved, no literal newline (single-line by grammar).

| Input | Value |
| --- | --- |
| `literal: 'hello\nworld'` (literal backslash-n) | `hello\nworld` — twelve characters, backslash and `n` intact (US6.2) |
| `with_quote: 'it''s fine'` | `it's fine` (US6.3) |
| `padded: '  spaces  '` | `  spaces  ` |

## Double-quoted (`"..."`)

| Escape | Result |
| --- | --- |
| `\\` | `\` |
| `\/` | `/` |
| `\"` | `"` |
| `\n` | LF |
| `\t` | TAB |
| `\r` | CR |
| `\uXXXX` | code point, 4 hex digits |
| `\UXXXXXXXX` | code point, 8 hex digits |

| Input | Value |
| --- | --- |
| `escaped: "hello\nworld"` | contains a real LF (US6.4) |
| `with_quote: "she said \"hi\""` | `she said "hi"` |
| `unicode: "smiley: ☺"` | `smiley: ☺` |
| `padded: "  hello  "` | `  hello  ` (US6.1) |

## Malformed (§4.7, §8.5, §11.3) — all `MalformedQuotedStringError`

At an inline position only:

| Condition | Input | `escape` | `code_point` |
| --- | --- | --- | --- |
| unterminated | `key: "unterminated` | `None` | `None` |
| trailing content after close | `key: "a" trailing` | `None` | `None` |
| trailing content after close (tab, not ASCII space) | `key: "a"\tx` | `None` | `None` |
| invalid / incomplete escape | `k: "a\xb"` | `"\\x"` | `None` |
| `\U` above U+10FFFF | `k: "\U00110000"` | `"\\U00110000"` | `0x110000` |
| escape decodes to a surrogate | `k: "\ud800"` | `"\\ud800"` | `0xD800` |

US6 scenarios 5, 6, 7.

**Surrogates (D3)**: every `\u` escape decodes independently. A surrogate code
point is an error whether or not it is half of what would be a valid UTF-16
pair. v1.1 does **not** combine pairs. Use `\U0001XXXX` or the literal
character. (Surrogate-pair combining is a v1.2 candidate — out of scope.)

## The quote-guard rule (§4.1, R-10)

Normative, **not expressible in PEG**. Implemented as a **visitor post-check**,
not a grammar rule:

> whenever the `data` matched by `key_value`'s second alternative, or by
> `list_item`'s inline `value`, begins with `'` or `"`, that is a
> `MalformedQuotedStringError` — not a valid scalar value.

This is how an unterminated inline quote becomes an error at all: `quoted_value`
simply fails to match and the line falls through to `data`, which would
otherwise swallow the opening quote as literal text.

Position: the opening quote character. The check is line-local and consults
nothing outside the current line, so the grammar stays context-free at the
lexing level (constitution V).

**Trailing content** (`key: "a" trailing`) is the PEG stranding case instead:
`key_value`'s first alternative matches `key: "a"` and then `~" *"` cannot reach
end-of-line, so the whole `line` sequence fails. Contract 05 / R-09 classify a
per-line `IncompleteParseError` as this error.

A negative lookahead in the grammar (`data = !~"['\"]" text`) was rejected: it
makes the line fall through to a different alternative rather than raising,
reintroducing exactly the silent fallthrough D2 removed.

### What the quote-guard reports: diagnosing the fallthrough

The grammar's `escape_seq` only admits the eight valid escapes, so a double-
quoted value containing an **invalid or incomplete** escape (`k: "a\xb"`,
`k: "a\u12"`) never matches `double_quoted` at all: `quoted_value` fails, the
line falls through to `key_colon ws data`, and the value reaches the
quote-guard, **not** `decode_double_quoted` (verified 2026-09-23 against the
transcribed grammar). The guard is therefore the only place that can populate
`.escape` for those rows, and "begins with a quote" alone cannot tell an
invalid escape from an unterminated string.

The guard diagnoses the text with a left-to-right scan from the opening quote
(`quoting.diagnose_malformed(text) -> str | None`, a pure function beside
the decoders):

1. **Double-quoted**: on each `\`, check the following characters against the
   §4.7 table. The **first** invalid or incomplete escape wins: `escape` is the
   backslash plus the characters examined before the failure (`"\\x"` for
   `\x`, `"\\u12"` for `\u12"`, `"\\"` for a backslash at end of line);
   `code_point` is `None`. An unescaped `"` ends the scan.
2. If the scan reaches end of line without a defect or a closing quote, the
   value is **unterminated**: `escape=None`, `code_point=None`.
3. **Single-quoted** values have no escapes; the only reachable diagnosis is
   unterminated.

A value that the scan finds well-formed **and** terminated is unreachable on
this path — it would have matched `quoted_value` — so the scan must be written
without that branch rather than with a pragma (constitution III). Out-of-range
code points (`\U00110000`) and surrogates (`\ud800`) **do** match the grammar
and are reported by `decode_double_quoted` as specified above; the two paths
partition the malformed cases between them.

Alternative considered and **not applied**: widen `escape_seq` to
`'\\' ~"."` so every backslash sequence matches and the decoder validates
all escapes in one place. It is simpler, but it changes §4.1's grammar as
printed, which this feature transcribes. Recorded as an open item for the
principal (plan.md § Edge Cases & Error Handling), not adopted.

## Completeness (§9.3, §4.1)

A quoted inline value is **complete**: its `TextLeafNode` has `quoted=True` and
`can_add_node` returns `False` for every candidate, at every level. The
candidate is re-offered up the tree by §9.2 and, the owning node being closed,
raises `OutOfContextNodeError`.

| Input | Result |
| --- | --- |
| `key: "a"\n  b` | `OutOfContextNodeError` (US6.8) |

## Whitespace around quotes

`ws?` before a quoted value — `key:"value"` is valid (§7.5, `todo.txt` S1).
`~" *"` after the closing quote — trailing spaces are allowed and consumed;
anything else is trailing content.

## Serialization inverse

`dumps` must produce values this contract decodes back identically — see
Contract 07 (§11.2.1 rules B, C, E, F, and the single-quote preference).

## Test obligations

- Every table row above.
- Guard-path diagnosis: `k: "a\xb"` → `escape="\\x"`; `k: "a\u12"` →
  `escape="\\u12"`; `k: "abc\` → `escape="\\"`; `k: "a\xb` (invalid escape
  **and** unterminated) → `escape="\\x"` (first defect wins); `k: "abc` and
  `k: 'abc` → `escape=None`. Each at an inline `key:` position and after `- `.
- Round-trip: `loads('k: ' + dumps_quoted(s))['k'] == s` over a corpus of
  strings containing quotes, backslashes, control characters, and astral-plane
  characters.
- Bare-line non-decoding: for each malformed inline case, the same text at a
  root-scalar / block / continuation position parses to literal text.
- US6's ten acceptance scenarios.
