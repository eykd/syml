# SYML Specification — Review Findings (pre-1.0 draft, reviewed as v1.0)

**Date:** 2026-09-13
**Subject:** `SYML-SPECIFICATION.md` pre-release draft (labelled v1.0 when
reviewed); the text released as 1.0 incorporates the findings below.
**Method:** The §4.1 grammar was transcribed verbatim into Parsimonious, §9.2–9.4 were implemented literally as a tree builder, and every input/output example in the spec plus ~40 edge probes were run through (a) the spec grammar, (b) the literal §9 algorithm, and (c) the shipped `syml` 0.6.2 `loads`. Four review passes (grammar vs prose, algorithm vs rules, round-trip/API, safety) then worked from that table. Findings below cite the harness where a run exists; the rest are marked prose-only.

Severity: **BLOCKER** = the spec contradicts itself, or an example cannot be produced by its own rules. **MAJOR** = behavior a conforming implementation must decide but the spec does not state, or a safety hole. **MINOR** = clarity or cosmetics.

Every finding lists the resolution applied in v1.1. Where a fix would add syntax rather than resolve a contradiction, v1.1 documents the limitation and the syntax is filed as a v1.2 candidate at the end.

> **2026-09-24 amendment (D18, D19).** Two decisions made after this review, before 1.0.0 shipped, supersede part of it. The trigger was interactive-fiction dialogue written in SYML: `- "Late for what?"` and `- choice: "I got held up."` are indistinguishable from quoted-string values, so no decoding rule could keep the quotation marks the author wrote. **D18** removes quoted strings entirely: every inline value and every bare line is the literal text on the page, `'` and `"` have no meaning, and `MalformedQuotedStringError` no longer exists. That supersedes D2, D3, and D17 and closes M1, M2, M3, and M19 by removal. Quoting was the spec's "modest extension"; 0.6.2 never had it, and it was the source of three round-trip defects at the list-item position. **D19** makes the same dialogue safe on the key side: a mapping key contains no uppercase or titlecase letter, so `Listen: here's what you need` is text rather than a mapping. The decisions table below records both; the D2/D3/D17 rows and the M1/M2/M3/M19 findings are annotated in place and otherwise left as written.

> **2026-09-24 amendment (D20-D25).** A second, larger amendment, made the
> same day as D18/D19 but after a dedicated break-test campaign (`syml-xreq`,
> 24 findings) probed the 1.0 rules the D18/D19 pass did not touch. The
> campaign's single organizing rule, ratified by the principal: **values are
> just text**. Once a value is text, it is never reinterpreted — structure is
> lexed only at a block's first line and at inline positions; every later
> line at or past the value's baseline joins it as text no matter what it
> would otherwise lex as (D21). Around that rule: the key pattern tightens to
> exactly `[a-z][a-z0-9_-]*` (D20, superseding D15 and D19); a blank line
> inside an open value is a paragraph break, not simply discarded (D22,
> superseding D12); comments are restored but scoped to column 0 only,
> reversing the brainstorm's initial "delete comments" reading of
> `syml-xreq.21` on the principal's explicit ruling (D23); a tab becomes
> separator whitespace after `key:`/`-` (D24, superseding D5); and children
> must be strictly deeper than their parent, list items included, restoring
> §4.2 rule 5 and §9.3's KeyValue row over an undocumented `>=` carve-out in
> the code (D25). The decisions table below records D20-D25; the D5, D12,
> D13, D15, D19 rows and the M6, M20, M21, M24, and B9 findings are annotated
> in place and otherwise left as written.

---

## Design decisions made in this review

These are judgment calls the spec did not make. Each is reversible; they are listed first so they can be overruled.

| # | Decision | Alternative not taken |
|---|----------|-----------------------|
| D1 | v1.1 is a consistency release. No new syntax. Empty list, empty mapping, keys with whitespace/colon/leading `#`, and quoted keys stay unrepresentable and are documented as such; `dumps` raises on them. | `[]`/`{}` tokens and quoted keys (v1.2 candidates, below). |
| D2 | **Superseded by D18 (2026-09-24): there are no quoted strings.** Quoted strings are recognized only at an inline position, immediately after `key:` or `- `. At such a position, a value whose first character is `'` or `"` MUST be a well-formed quoted string ending the line (optional trailing spaces). Unterminated quotes, trailing text after the closing quote, invalid escapes, and out-of-range code points are all `MalformedQuotedStringError`. No silent fallthrough to literal text. Bare lines (root scalars, block values, continuation lines) are never quote-decoded; a leading `'` or `"` there is ordinary text. | (i) Document the v1.0 grammar's silent fallthrough (predictability hazard; rejected). (ii) Apply the quote rule to bare lines too (audit showed this makes apostrophe-initial prose such as `'Tis` an error and silently decodes quoted continuation lines; rejected). |
| D3 | **Superseded by D18 (2026-09-24): there are no escape sequences.** Escapes MUST NOT decode to a surrogate code point (U+D800–U+DFFF), paired or not. Supplementary-plane characters use `\U0001XXXX` or are written literally. | JSON-style combining of `\uD83D\uDE00` pairs (adds decoder state; deferred to v1.2 if wanted). |
| D4 | Trailing whitespace on unquoted values is preserved (as §7.5 and the grammar already say). Leading whitespace after `key:`/`- ` is consumed by the required separator. §4.7's "trimmed" wording is corrected. | Trim both sides (would contradict the grammar and §7.5's editor note). |
| D5 | **Superseded by D24 (2026-09-24).** A tab immediately after `key:` or `-` is not separator whitespace; the line is scalar text per §7.6, same as `key:value`. Only a tab in leading indentation is an error. | Make the post-marker tab an error too (SAFETY-2); rejected as inconsistent with the §7.6 fallthrough rule for every other malformed structural line. |
| D6 | A zero-length unquoted inline value (`key: `, `- `) is the same as no inline value (`key:`, `-`). Only `key: ""` is an explicit empty string. | Treat `key: ` as a present empty value that closes the node (makes an invisible trailing space change document validity). |
| D7 | §8.1 (bad indentation) and §8.2 (context violation) both raise `OutOfContextNodeError`; there is no separate `InconsistentIndentationError`. Both are "no place in the tree". | A distinct class per §8 subsection (needs extra classification logic the algorithm does not naturally produce). |
| D8 | Mapping key order is insertion order, guaranteed. | Keep "MUST NOT depend on ordering" (contradicts §1.1 and every example). |
| D9 | Control characters other than LF are allowed verbatim in values, including NUL, and the spec says so. | Reject C0 controls in values (would invalidate currently-valid documents; can be revisited). |
| D10 | Implementation limits are SHOULD with concrete defaults (500 depth, 1 MiB line, 10 MiB document) and a named `DocumentLimitError`. | MUST limits (over-constrains embedded uses). |
| D11 | The baseline of a multiline value is the indentation of the first line of the value that occupies a line of its own: for an inline value, its first continuation line; for a block value, its first block line; for a root scalar, its first line (baseline 0). Lines at or beyond the baseline join (extra indentation preserved); a line below the baseline ends the value and is re-offered to the owning container. | Baseline set by the first *continuation* line even for block values. The audit showed this turns `key:\n  first\n    indented\n  back` into a parse error and flattens relative indentation in block values; rejected. |
| D12 | **Superseded by D22 (2026-09-24).** Blank and whitespace-only lines inside a multiline value are discarded: they neither add a line nor end the value. A value containing consecutive newlines is written inline as a double-quoted string with `\n` escapes. | A blank line between two continuation lines contributes an empty line (would need a second baseline rule for blank lines; deferred). |
| D13 | **Superseded by D21 (2026-09-24).** Every line is lexed independently, with no context. A line at a continuation position that lexes as structure (`key: v`, `key:`, `- x`) is structure, and following a closed key-value pair or list item it is a parse error. Block form is for plain prose; a value with a line that would lex as structure, or that begins with `#` or `//`, is written inline as a double-quoted string. | Re-lex continuation lines as raw text (context-sensitive grammar; also silently absorbs `key: v\n  nested: x`, a likely authoring error). |
| D14 | Leading whitespace of a line is the maximal run of U+0020 and U+0009 before any other character. A line whose leading whitespace is the whole line is blank (§4.4) and is discarded before any other check. Otherwise, a tab anywhere in the leading whitespace is `TabIndentationError`, including a tab that begins the content of a continuation line. A value that must begin with a tab is quoted. Tabs after the separator space (`key: \tv`) are value content and are not normalized. | Treat tab-only lines as an error; treat a tab-initial continuation line as content. |
| D15 | **Superseded by D20 (2026-09-24).** The whitespace excluded from keys is the set of code points with the Unicode `White_Space` property (U+0009–U+000D, U+0020, U+0085, U+00A0, U+1680, U+2000–U+200A, U+2028, U+2029, U+202F, U+205F, U+3000). The grammar's `\s` denotes exactly this set. | ASCII-only `\s` (Go RE2 and Rust `regex` default), which would make `key\u00a0name: v` a mapping in one implementation and a scalar in another. |
| D16 | The document rule is `document = (line "\n")* line?` and end-of-input is `\Z` (absolute end), so no repeated expression is nullable and `$`'s engine-dependent before-final-newline behavior is avoided. | `lines = line*` with a nullable `line` (Parsimonious tolerates it; pest rejects it at build time). |
| D17 | **Superseded by D18 (2026-09-24): §11.2.4 is folded into §11.2.1, which now states the unrepresentable set for every position.** A root scalar cannot be quoted (D2), so `dumps` raises `UnrepresentableValueError` for a root string that would lex as structure or a comment, contains control characters, has leading/trailing whitespace on a line, or is exactly `''`/`""` (§11.2.4). Such values are carried as mapping or list values instead. | Allow quoting at the root position (adds a third quoting context and a new grammar rule). |
| D18 | *(2026-09-24)* SYML has no quoted strings. Every inline value (after `key: ` or `- `) and every bare line is the literal text on the page; `'` and `"` have no meaning at any position, there are no escape sequences, and `MalformedQuotedStringError` does not exist. `dumps` writes a string containing `\n` in block form (`key:`/`-` on its own line, each line indented two spaces past it); a root scalar is always block form; the unrepresentable set is stated per position in §11.2.1 (control characters other than LF/TAB; a first line beginning with a space or tab; in block form a blank, tab-initial, comment-shaped, or structure-shaped line; a structure-shaped single-line list item). Reason: interactive-fiction dialogue (`- "Late for what?"`, `- choice: "I got held up."`) is indistinguishable from a quoted-string value, so no decoding rule can keep the quotes the author wrote; quoting was the spec's "modest extension", 0.6.2 never had it, and it caused three round-trip defects at the list-item position. Supersedes D2, D3, D17; closes M1, M2, M3, M19 by removal. | Keep quoting with a heuristic (e.g. decode only when the closing quote ends the line, or only when the value contains no interior quote). Rejected: every heuristic misreads some real dialogue line, and a rule that silently strips an author's quotation marks violates §1.1's predictability principle. |
| D19 | **Superseded by D20 (2026-09-24).** *(2026-09-24)* A mapping key contains no code point of Unicode General_Category `Lu` or `Lt` (the check is exactly `unicodedata.category(c) in {'Lu', 'Lt'}` for any character, applied outside the PEG to the key matched by `key_value` and `section`). A line whose would-be key violates this is not structure; it is literal text, as if it had lexed as `data`: `- Listen: here's what you need` → `['Listen: here\'s what you need']`, `Été: chaud` → the scalar `'Été: chaud'`, while `look-in-dark:`, `effect: x`, and `名前: x` stay keys (`Ⅻ` is `Nl`, so it is a valid key; `É` and `ǅ` are not). `dumps` raises for a key with an uppercase or titlecase letter. Residual hazard, stated in §4.5: a prose line beginning with a lowercase word followed by `: ` still lexes as a key. Breaking change vs 0.6.2 (`Name: x` was a mapping). | Keep case-insensitive keys and accept the prose ambiguity (a capitalized `Word: …` line in block-form dialogue would be a nested mapping or an `OutOfContextNodeError`, and D18 removed the only way to force it literal). Rejected: the whole point of D18 was to let dialogue be written as it reads. |
| D20 | *(2026-09-24)* A key is exactly `[a-z][a-z0-9_-]*`, preceded only by indentation spaces; any other would-be key line is text; `dumps` refuses other keys. | Keep D19's "no `Lu`/`Lt`" rule plus a leading-bracket/quote exclusion (`syml-xreq.16` option b). Supersedes D15, D19. Breaking change: `Name:`, `firstName:`, `URL:`, `1:`, `e.mail:`, `名前:` stop being keys. Inside a list item the effect is asymmetric: a non-pattern **first** key makes the whole record one string with no error (`- containerPort: 80\n  protocol: TCP` → `["containerPort: 80\nprotocol: TCP"]`, raised in 1.0), while a non-pattern later key raises with a hint. |
| D21 | *(2026-09-24)* Values are just text: structure is lexed at a block's first line and inline only; once a value is text, every line at or past its baseline is text until a line below it; a root document whose first line is text is text throughout. | Keep per-line lexing and add an error hint (`syml-xreq.22` option a). Supersedes D13. Breaking change: deeper structure-shaped lines after a text value join it; a line indented past a sibling that holds an inline value is absorbed silently. Lexing still runs first, so a long `- - - …` line still raises `RecursionError` inside a text value; an iterative list-marker rule that would lift this is a 1.x candidate. |
| D22 | *(2026-09-24)* A blank line between two lines of the same value is an empty line of that value, one per physical line; blank lines before a value's first line, after its last, or between items/keys are inert; `dumps` writes paragraph breaks. | An explicit paragraph marker line (`syml-xreq.15` option c). Supersedes D12. Breaking change: `k:\n  a\n\n  b` was `"a\nb"`, is now `"a\n\nb"`. |
| D23 | *(2026-09-24, principal ruling, superseding the "no comments" reading of `syml-xreq.21`)* Comments are column-0 only: a line whose first character, with no indentation, is `#`, or whose first two characters are `//`, is a comment, skipped as if absent anywhere in the document, including between two lines of an open value (not a paragraph break). Every indented `#`/`//` line and every `#` after a key or marker is text. | Remove comments entirely (the first reading of the `syml-xreq.21` ruling; overruled because its "all loud" premise was false); `#` only; comments only between structure entries. Supersedes §4.3's "a line beginning with `#` or `//` is always a comment, at any indentation" and closes M6's skip-the-continuation fix and B9's exception. Breaking change: column-0 comment lines, file headers included, keep working. An **indented** `#`/`//` line changes meaning: inside a value it is kept as text (`- tag line\n  #winning` → `["tag line\n#winning"]`, where 1.0 dropped it); at a container's level after its first entry it raises; and, silently, as the first line of a block it makes that block one string (`a:\n  # s\n  b: 1` → `{"a": "# s\nb: 1"}`). And, silently one level down, a `#`/`//` after `key:` or `-` is that key's or item's text value and takes in the block under it (`server: # prod\n  host: x` → `{"server": "# prod\nhost: x"}`, raised in 1.0). A root scalar with a line that begins with `#` or `//` is unrepresentable by `dumps` (§11.2.1 item 9). |
| D24 | *(2026-09-24)* A tab is separator whitespace after `key:` and `-` (`ws = [ \t]+`); a marker followed only by spaces/tabs is bare; a tab in indentation still raises. A separator tab counts as one column for §6.2's sibling column. | Make a post-marker tab an error (v1.2 candidate 4). Supersedes D5. Breaking change: `k:\tv` was `"k:\tv"`, is now `{"k": "v"}`; `k: \tv` was `{"k": "\tv"}`, is now `{"k": "v"}`. After `-\tk: v`, a sibling key goes at column 2; a line an editor shows aligned under `k` at a tab stop joins `v` silently. |
| D25 | *(2026-09-24)* Children are strictly deeper than their parent, list items included; the YAML indentless sequence is an error with a hint. §6.2's `- key:` sibling-column rule stands. | Keep the undocumented carve-out and add a KeyValue row to §9.3 (`syml-xreq.3` recommendation). Restores §4.2 rule 5 / §9.3 over the code's undocumented behavior. Breaking change: `k:\n- a` was `{"k": ["a"]}`, is now `OutOfContextNodeError`. |
| D26 | *(2026-09-25)* `OutOfContextNodeError` gets hint (c) when the failing line, or the line above (hint (a)'s look-back), matches `^[a-z][a-z0-9_-]*:\S` or `^-\S`: "a key or list marker needs a space after it". Grammar unchanged. | README bullet only (`syml-cjk2.10` option B). `port:8080` alone still parses silently as text (§7.6, D21); the README "Coming from YAML" section gains a bullet warning about it. |
| D27 | *(2026-09-25)* Hint (d) when the failing line's text (after indentation) starts with `#` or `//`: "comments must start at column 0; an indented `#` line is text" (consistent with D23). Hint (e) when that text is `---` or `...`: "SYML has no document markers". | Rely on the README (`syml-cjk2.11`). Error text only. |
| D28 | *(2026-09-25)* README "Coming from YAML" gains two bullets: trailing whitespace on a value line is kept; an over-indented line joins the value above it as text (which is how YAML-style sub-bullets behave). | Leave undocumented (`syml-cjk2.12`). Docs only; no behavior change. |
| D29 | *(2026-09-25)* `dumps` messages stop calling a whitespace-only line "blank": that case says "contains a non-empty whitespace-only line". The family-6 message ("begins or ends with a blank line") names a trailing newline when that is the cause. | Leave the wording (`syml-cjk2.13` option B). Message text only. |
| D30 | *(2026-09-25)* `UnrepresentableValueError` and the `dumps` `TypeError` render `str(e)` as the message alone, not a tuple repr, and the message names the data path in subscript form, e.g. `at ['a']['b'][1]` (root value: no path clause). `UnrepresentableValueError` gains `.path`: a tuple of keys (`str`) and list indexes (`int`) from the root, `()` for the root. The `TypeError` stays a plain builtin constructed with the message only: no `.path`, no subclass, so no new class name under §11.3. | `str(e)` fix only, or defer the path to a minor release (`syml-cjk2.14` option B and its recommendation). The one API addition in round 2. |
| D31 | *(2026-09-25)* `EncodingError` says "Invalid UTF-8 (byte 0xe9); save the file as UTF-8", naming the first offending byte in lowercase hex, instead of "Invalid encoding". | Leave it (`syml-cjk2.15` option B). Message text only. |
| D32 | *(2026-09-25)* `DuplicateKeyError`'s message adds "(first defined at line N)". The spec §8.3 example and Contract 03's message rows change in the same commit as the code. | Leave it (`syml-cjk2.16` option B). |
| D33 | *(2026-09-25)* `ParseError.line_text` is the normalized line (BOM stripped), documented: on line 1 of a BOM-led document `column` is one greater than its index into `line_text`. `__str__` centres its excerpt window with the BOM offset subtracted. Positions keep their raw-input coordinates. | Prepend the BOM to `line_text` on line 1 (`syml-cjk2.17` option B; puts an invisible character in the text). Adopts options A and C together. |
| D34 | *(2026-09-25)* Refines D-less `syml-cjk2.5`: a `filename` passes through `error_message`/`ParseError.__str__` whole up to 1024 code points; past that it is windowed from its **tail** — `'…'` plus its last 1023 code points — via a dedicated `_truncated_filename_window`, so a path's basename always survives. `syml-cjk2.5`'s original 80-code-point head-centered `_truncated_window(filename, center=0)` cut the basename off any real-world absolute path longer than 80 characters (routine for CI runner paths), silently making `str(e)`'s `path:line:col` form unclickable. | Keep `_truncated_window`'s centered/head-eliding treatment and only widen it (`syml-cjk2.19`'s narrower option); rejected because centering still elides the tail for any filename past the (wider) width, and the basename is the part a reader actually needs. |

---

## BLOCKER

### B1 — §4.1 grammar does not load (three independent defects)
Sources: harness Findings 1–2 (TRANSCRIPTION_NOTES in `spec_grammar.py`); G1, G2.
1. `list_item = "-" ws value / "-" &eol` and `key_value = ... / ...` are read by Parsimonious as a sequence followed by a dangling `/`; sequence alternatives must be parenthesized.
2. `escape_seq` uses bare regex classes (`[\\/"/nrt]`, `[0-9a-fA-F]{4}`) that are not grammar atoms; they must be `~"..."` terminals. `[\\/"/nrt]` also lists `/` twice (seed 14).
3. `~'[^"\\]'` becomes the unterminated class `[^"\]` after Parsimonious's string unescape.
**Fix:** rewrite §4.1 (full corrected grammar in v1.1; load-tested against all 98 harness examples).

### B2 — §4.1 cannot parse any multi-line document
Source: harness Finding 3; G3. `line = ... &eol` is a lookahead; nothing consumes `\n`, so `lines = line*` stops after line one and every example after §2.1 is unparseable by the spec's own grammar.
**Fix:** superseded by D16 (`document = (line "\n")* line?`, with `eol` lookahead-only). §7.6's argument about `&eol` guards still holds for the inner structural rules.

### B3 — Single-quote escape needs four quotes, not two
Source: harness Finding 4, row `4.7-single-with-quote`; G4. `(~"''" "''" / ...)` is regex-two-quotes followed by literal-two-quotes. `'it''s fine'` strands the parse instead of producing `it's fine`.
**Fix:** `single_quoted = "'" ("''" / ~"[^'\n]")* "'"`.

### B4 — §9.3 `>=` sibling acceptance: §8.1 and §4.2's own error examples parse cleanly
Source: harness Finding 6, rows `8.1`, `4.2-invalid`, probe `note: hello\n  more: text`; H-ALGO-1, -2, -4, -7. With `>=`, a line shallower than its siblings but deeper than some ancestor is silently adopted by that ancestor. `parent:\n  child1: value\n child2: value` yields `{"parent": {"child1": "value"}, "child2": "value"}`; the 3-space variant becomes an extra sibling; `note: hello\n  more: text` becomes a second root key. Shipped impl has the identical bug (`ParentNode.can_add_node`).
**Fix:** `==` for List and Mapping rows; "no partial-indentation matching" sentence; "a KeyValue/ListItem with a child is closed" sentence. Verified in the rewritten tree builder: all three now raise, all §5/§6/§12 examples unchanged.

### B5 — §5.3 "below baseline terminates the value" is unimplementable from §9.3
Source: harness Finding 12, probes `key: a\n    b\n  c`, `key: a\nb`, `hello\nworld`; H-ALGO-3, -5, -6. The TextLeaf row has no Conditions cell, so every text line joins every preceding text value regardless of level, and §5.1 rule 1 is never enforced.
**Fix:** TextLeaf row gets an explicit condition (anchor level + baseline, per D11); §5.3 rewritten so the terminating line is re-offered to the owning container. A root scalar's first line sets baseline 0, so `hello\nworld` and `hello\n  world\nagain` join (the second as `"hello\n  world\nagain"`), while `key: a\nb` raises because `b` is not deeper than `key`. Consequence stated in §5.3: `key:\n  first\n    indented\n  back` keeps its relative indentation; `key:\n  a\n b` raises.

### B6 — §9.3 has no duplicate-key rule; §8.3 says MUST raise
Source: harness Finding 7, rows `8.3`, `a: 1\na: 2`; H-ALGO-8; API-12. Both the literal algorithm and the shipped impl are last-write-wins. Detection cannot live in `as_data()` (position lost; Source keys collapse identically).
**Fix:** Mapping row checks key presence at incorporation time and raises `DuplicateKeyError`. Equality is code-point equality, case-sensitive, no Unicode normalization (SAFETY-8).

### B7 — Tabs: §13.2 "tab normalization" contradicts §4.2/§8.4, and neither §4.1 nor §9 can raise the §8.4 error
Source: harness Finding 8, row `8.4`; SAFETY-1, SAFETY-2; H-ALGO remaining-mismatch note. §4.1's `indent = ~" *"` does not match a tab, so `\tkey: value` falls through to a literal scalar; the shipped impl expands tabs to four spaces and parses it as a mapping; the prose says error. Three-way split.
**Fix:** §13.2 bullet rewritten (no normalization exists); new §9.0 pre-processing step classifies blank lines first, then scans leading whitespace for tabs and raises `TabIndentationError` before the grammar runs (D14). Post-marker tabs per D5.

### B8 — Header says v0.6.2 is the reference implementation; §14 says v1.0 breaks compatibility with it
Source: harness Findings 9–11, 13 (bare `-` unsupported, quoted strings undecoded, `None` for empty documents, no CR/BOM handling); API-1.
**Fix:** status line now says no conforming implementation exists and v0.6.2 predates the spec.

### B9 — §4.5 promises any printable punctuation in keys; §4.1 makes `#`/`//`-initial keys unreachable (severity: MAJOR on re-weighing; kept here for numbering)
**Superseded by D20/D23 (2026-09-24):** moot under D20/D23 — the key pattern excludes punctuation generally, and `#`/`//` is unreachable as a key start for the same column-0-comment reason as before.
Source: G7 (probe `#tag: value` matches `comment`); API-7. `comment` is tried before `structure`.
**Fix (D1):** §4.5 gains an explicit exception; quoted keys filed as v1.2 candidate.

### B10 — §4.7 "whitespace trimmed from unquoted values" vs §7.5 "trailing whitespace preserved" vs grammar `data = text`
Source: seed 2; API-4; harness rows `key:  padded  `, `key: value ` (grammar and §9 preserve).
**Fix (D4):** one rule in §7.5, §4.7 references it.

---

## MAJOR

### M1 — Quoted strings may span lines
*Closed by D18 (2026-09-24): quoted strings were removed.*
Source: G5; probes `key: 'multi\nline'`, `key: "multi\nline"` (grammar swallows the next line, including its indentation). Contradicts the line-based model in §2 and §4.2.
**Fix:** `\n` excluded from both quoted-string classes; prose says a quoted string ends on its line and `\n` is written as an escape.

### M2 — Malformed quoted values: `key: "a" trailing` strands the parse, `key: "unterminated` silently becomes literal text, `\x` is unspecified
*Closed by D18 (2026-09-24): quoted strings were removed; `key: "a" trailing` and `key: "unterminated` are now the literal values `"a" trailing` and `"unterminated`.*
Source: harness probes (SPLIT); G10; seed 5.
**Fix (D2):** all three are `MalformedQuotedStringError` at inline positions. Grammar allows optional trailing spaces after the closing quote and nothing else. Implementations detect the unterminated case by checking whether an unquoted inline `data` match begins with a quote character. §7.6 gains an explicit exception sentence linking to this rule, since it is the one place SYML does not take a malformed line literally.

### M3 — `\U` above U+10FFFF and surrogate escapes are unspecified
*Closed by D18 (2026-09-24): escape sequences were removed.*
Source: probes `\U00110000` (literal §9 raises bare `ValueError`), `\uD800` (unpaired surrogate passes through, not encodable as UTF-8); SAFETY-6, SAFETY-7.
**Fix (D3):** both are `MalformedQuotedStringError`.

### M4 — §7.2 "list markers in values are literal text" contradicts the grammar and §6.2 for list-item values
Source: probe `- - x` → `[["x"]]` in grammar, §9, and impl; G9; API-5. The rule is true only for mapping inline values (`key_value` goes straight to `data`); list-item inline values re-enter `structure` (that is how `- name: Alice` works).
**Fix:** §7.2 rewritten to state the asymmetry; serializer rule D in §11.2.1.

### M5 — `key: ` and `key:` behave differently by one invisible trailing space
Source: H-ALGO-9; seed 11; probes `key: `, `- `.
**Fix (D6).**

### M6 — Continuation line starting with `#`/`//` silently vanishes from a multiline value
**Superseded by D23 (2026-09-24):** closed by D23 — an indented `#`/`//` continuation is text, not skipped; a column-0 one is a comment, skipped by design.
Source: probe `key: value\n  # indented hash line\n  more` → `{"key": "value\nmore"}` in §9 and impl; G8; H-ALGO-12. Never stated.
**Fix (D12, D13):** §5.1 rule 4 and §9.1 note: comments and blank lines are skipped at any indentation and never affect a continuation baseline. To include such a line, or a paragraph break, write the value inline as a double-quoted string.

### M7 — Mapping ordering disclaimed but relied on everywhere
Source: seed 9; API-2, API-13.
**Fix (D8).**

### M8 — Empty list and empty mapping unrepresentable; `dumps` undefined
Source: API-3, API-8; seed 8.
**Fix (D1):** §11.2.2 documents the gap and makes `dumps` raise `UnrepresentableValueError`; `[]`/`{}` filed as v1.2 candidate.

### M9 — No normative quoting rules for `dumps`; round-trip undefined
Source: API-4, API-5, API-6.
**Fix:** §11.2.1 quoting table (empty string, leading/trailing space, control characters, values that would parse as structure at a `value` position, values starting with a quote, the literal strings `''` and `""`). `dumps` MUST NOT use block continuation for embedded newlines.

### M10 — Error taxonomy: only one named error for at least six required conditions
Source: seed 12; API-9, API-10.
**Fix (D7):** §11.3 names `ParseError`, `OutOfContextNodeError`, `DuplicateKeyError`, `TabIndentationError`, `MalformedQuotedStringError`, `DocumentLimitError`, and `UnrepresentableValueError` (raised by `dumps`, not a `ParseError`). Names are normative.

### M11 — CR/BOM normalization has no home in the algorithm; impl does none of it
Source: harness Finding 13; SAFETY-3, SAFETY-10; G12.
**Fix:** new §9.0 Pre-Processing (BOM at index 0 only, exactly one; CRLF/CR → LF; tab scan). §4.1 states it assumes normalized input. BOM-only document is the empty document.

### M12 — Line separator undefined; `str.splitlines()` silently miscounts lines
Source: SAFETY-4 (reproduced off-by-one `Pos` with U+2028 in a value, `utils.py`/`basetypes.py`).
**Fix:** §13.3: a line boundary is exactly U+000A after normalization; U+000B, U+000C, U+0085, U+2028, U+2029, U+001C–1E never split lines; implementations MUST NOT use general-purpose splitlines routines.

### M13 — Encoding: "or platform-native encoding"; `load()` decode policy unstated
Source: seed 13; SAFETY-11.
**Fix:** UTF-8 only; `load()` decodes strictly and raises on invalid bytes.

### M14 — Control characters in values unspecified
Source: SAFETY-5 (NUL and DEL pass through in grammar, §9, and impl).
**Fix (D9).**

### M15 — No implementation limits; recursion depth is a crash, not an error
Source: harness Finding 14 (10k-deep inline list: `RecursionError` in the grammar itself; impl times out); SAFETY-9 (unterminated-quote failure cost super-linear to 2 MB).
**Fix (D10):** §13.4.

### M16 — Duplicate-key equality undefined
Source: SAFETY-8.
**Fix:** code-point equality (folded into B6).

### M17 — §9.2 pseudocode: `add_child` return value and routing of inline structural values unstated
Source: harness prose-silent list; H-ALGO-11. Only the "returns the tip" reading makes §5 work; only "inline structures route through the same algorithm" makes §6.3 work.
**Fix:** two sentences under §9.2.

### M18 — §4.2's own "valid" example is not valid SYML
Source: Forge audit; harness row `4.2-valid-verbatim`. The trailing `# Level 0` annotations are values per §4.3, so `parent:` has the inline value `# Level 0` and is closed; under v1.1 rules the example raises. §8.1–8.4 carry the same `# ERROR:` trailers (harmless only because those lines error anyway; §8.3's duplicate value becomes `value2     # ERROR: ...`).
**Fix:** strip trailing annotations from every example; put levels in prose. Sweep all ```syml blocks.

### M19 — Quoted continuation lines are silently decoded; quoted values can be continued
*Closed by D18 (2026-09-24): quoted strings were removed; `key: He said\n  'yes'` is now `{"key": "He said\n'yes'"}`, quotes kept, and `key: "a"\n  b` is `{"key": "\"a\"\nb"}`.*
Source: Forge audit, verified on both the v1.0 harness and the rewritten tree builder: `key: He said\n  'yes'` → `{"key": "He said\nyes"}` (quotes vanish); `key: "a"\n  b` → `{"key": "a\nb"}`.
**Fix (D2, D13):** quoting is recognized only inline. A bare line beginning with a quote is text. A quoted inline value is a complete value: a following deeper line is not a continuation (it is re-offered up the tree and, the node being closed, raises).

### M20 — Blank lines inside a multiline value vanish; paragraph breaks are unwritable in block form
**Superseded by D22 (2026-09-24):** closed by D22 — a blank line inside an open value is now a paragraph break, not discarded.
Source: Forge audit; `bio: para one\n\n  para two` → `{"bio": "para one\npara two"}` in both builders.
**Fix (D12):** stated in §5.1; `\n\n` is written inline in a double-quoted string.

### M21 — Key whitespace exclusion depends on the regex engine's `\s`
**Superseded by D20 (2026-09-24):** moot under D20 — the key pattern is exactly `[a-z][a-z0-9_-]*`, which contains no `\s`-class reference at all.
Source: Forge audit; `key\u00a0name: v` is a scalar under Python/JS `\s` and a mapping under Go RE2 / Rust `regex` defaults.
**Fix (D15).**

### M22 — `lines = line*` becomes a nullable repetition once `eol` is consumed; `~"$"` is engine-dependent
Source: Forge audit; Parsimonious stops on a zero-width iteration, pest rejects the grammar at build time.
**Fix (D16).**

### M23 — Inline key after `- ` sets the sibling column; `- ` spacing is load-bearing and unstated
Source: Forge audit; `-   name: Alice\n  role: admin` raises, `-   name: Alice\n    role: admin` parses.
**Fix:** sentence in §6.2; `dumps` emits exactly one space after `-` (§11.2.1).

### M24 — §7.6 oversells "prose values can contain colons" and §6.4 understates what is an error
**Superseded by D21 (2026-09-24):** changed by D21 — both examples now join as text (text-context), where 1.0 raised on the second.
Source: Forge audit; `a: Note\n  Warning: do not touch` raises under the closed-node rule, `a: Note\n  Big Warning: do not touch` joins; `a:\n  b: 1\n  plain` raises (text at a mapping's level).
**Fix (D13):** §7.6 sentence rewritten to say a continuation-position line that lexes as structure is structure; §6.4 notes plain text at a container's level is also an error.

---

## MINOR

- **m1** `comment = ~"(#|//+)+" text?` admits `#//#`; simplified to `("#" / "//") text?` (G6, seed 14).
- **m2** ListItem's empty value (`""`) never stated; §7.3 sentence added (H-ALGO-10).
- **m3** §11.1 lists "empty string if document is empty" as a fourth return shape; it is the scalar case (API-11).
- **m4** §10.3 Source-key equality means duplicate keys collapse in `as_source()`; detection must precede materialization (API-12; folded into B6).
- **m5** Tab after `key:`/`-` unspecified (G11; D5).
- **m6** `tox.ini` targets py39–311 while `requires-python >= 3.12`. Repo hygiene, not spec (seed 15, API-14).

---

## Out of scope (spec vs implementation gaps, recorded for a follow-up)

The shipped `src/syml` (0.6.2) diverges from v1.1 in every one of these, all confirmed by the harness:
- No quoted-string support at all (quotes and escapes returned verbatim); `key_value` requires a space after `:` even for quoted values.
- No bare `-` list marker (`-\n  block item` becomes the scalar `"-\nblock item"`; `-\n  - x` raises).
- Tabs in indentation expanded to four spaces instead of raising; `ws` accepts tabs.
- Duplicate keys overwrite silently.
- `>=` sibling acceptance (same bug as B4).
- No continuation-level check (same gap as B5).
- Empty/comment-only documents and `key:\n` return `None`, not `""` (a `pragma: nocover` branch that is routinely reached).
- No BOM stripping, no CRLF/CR normalization; source positions use `str.splitlines()`.
- No `dumps`/`dump`.
- Deep nesting recurses without limit.
- Also: `tests/test_nodes.py` is empty with a `.orig` beside it; `tox.ini` is stale.

## v1.2 candidates (new syntax; not in v1.1)

1. **`[]` and `{}`** as the entire value at a value position, meaning empty list / empty mapping. Closes M8. Cost: a string that is literally `[]` or `{}` must then be quoted; pressure toward general flow collections, which §1.2 rejects.
2. **Quoted keys** (`'key with spaces': value`, `"#tag": value`). Closes B9 and the key half of M8. Cost: `comment` precedence must except a line beginning with a quote character.
3. **Surrogate-pair combining** in `\u` escapes (JSON semantics). Not needed while `\U` exists.
4. **Post-marker tab as error** (SAFETY-2's stricter reading of D5).

## Verification record

- Pre-audit grammar (grammar lane's corrected §4.1, before D16 restructured the top rule): loads in Parsimonious; all 98 harness examples parsed at the grammar level; every non-error example produced its stated output through the v1.0-era literal §9 tree builder. Superseded by the v1.1 checks below.
- Rewritten §9.3/§5.3 tree builder (algorithm lane's build, prior to the audit-driven D11/D13 change): 61 pass / 3 fail / 34 unspecified over the 98 `examples.json` rows; the 3 failures were the B3 and B7 grammar-layer items, fixed separately in v1.1.
- Cross-vendor audit (OpenAI-family, read-only) of this report: 6 blind spots and 4 fix conflicts, all folded in as M18–M24 and D12–D16, plus the D2 scoping and D11 replacement. One citation error (M15's finding number) and one over-severity (B9) corrected.
- v1.1 text: the §4.1 grammar as printed loads in Parsimonious; all 54 ```syml blocks in the revised spec were extracted and parsed against it: 52 parse, and the 2 that do not are both the intentional `key: "a" trailing` error example. Every §N.N cross-reference in the text resolves to a heading (0 missing). Script: `verify_spec.py` in the session scratchpad.
- Anthropic-family top-rung second look (read-only) over the final diff, walking every example through the v1.1 §9.3/§5.3 text by hand: 3 critical (the §4.2 "valid" example raised under the new closed-node rule; the quoted-value completeness rule was prose-only; root scalars could not satisfy the `dumps` round-trip), 6 warnings, 5 notes. All applied; the root-scalar item became D17.
- v1.1 semantics were then machine-checked: a ~150-line tree builder implementing §9.0–9.4, §5.3 and the §4.7 error rules literally as written (`v11_builder.py`, session scratchpad) was run over every ```syml block that states an Output: 45 checked, 45 match, including every ERROR example. The audit and second-look probe inputs (quoted continuation, blank line in value, tab-only line, `-   name:` spacing, surrogate pair, NBSP in key) were also run and behave as the text says.
- **2026-09-24 (D20-D25) verification.** Unlike the v1.1 checks above, the D20-D25 spec text was **not** re-verified against a scratch harness: it was checked directly against the shipped `syml` code via `tests/test_spec_examples.py` (SC-005), the same test the released package's CI runs. Every fenced ```syml example whose stated Output/ERROR the shipped 0.x code does not yet produce is listed in that module's `PENDING` table, keyed by `(source, stated output)` and marked `xfail(strict=True)`, valued by the FR that will make it true; a Green leaf later in this feature deletes its own entries as each FR lands, and the release leaf's final run has an empty table. This is the SC-005 discipline: the spec's own conformance test is the harness, not a one-off script.
