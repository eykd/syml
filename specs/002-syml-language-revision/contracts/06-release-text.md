# Contract 06 — Release Text: Specification, Decision Record, Changelog, README, Tag

**Requirements**: FR-015, FR-016, FR-017 (§11.3 half), FR-018; US4 | **Findings closed**: `syml-xreq.8`, `.9` (text half), `.10` (docs), `.24`, `.3`/`.17`/`.20` (README halves) | **Research**: R-02, R-05, R-06, R-09, R-10, R-11, R-17, R-18

This contract is the checklist for every non-code artifact. Two leaves use it:
the **spec leaf** (first; `SYML-SPECIFICATION.md` + `SYML-SPEC-REVIEW.md`,
before any code, principle IV) and the **release leaf** (last; CHANGELOG,
README, CLAUDE.md, recursion figures, tag).

## A. `SYML-SPECIFICATION.md` (spec leaf)

Header stays "Version: 1.0" with `syml` 1.0.0 as the conforming reference
implementation (FR-018). Every fenced `syml` block that states an Output or
ERROR must be true of the shipped code at the end of the feature (SC-005);
`tests/test_spec_examples.py` enforces it. The spec leaf moves
`MINIMUM_EXAMPLE_COUNT` to the post-edit count and lists every example whose
output the code does not yet produce in a `PENDING` table
(`xfail(strict=True)`, keyed by `(source, stated output)`, value = the FR that fixes it);
later leaves delete their entries and the release leaf deletes the table
(plan.md § Leaf Ordering).

| Section | Change |
| --- | --- |
| §2 | Keep "A **comment**" in the line kinds, restricted: a line whose first character, with no indentation, is `#`, or whose first two characters are `//` (principal ruling 2026-09-24). §2.1's unlabelled block keeps its column-0 `#` labels: they are comments under the revised §4.3. |
| §4.1 | Print Contract 01's grammar, with `line` in its parenthesized form (`comment / (indent (structure / data))`, R-18), `eol`'s regex as the raw literal `~r"\Z"` (the current §4.1 prints `~"\Z"`, which does not load under the repository's `error::SyntaxWarning` policy; Contract 01) and `document` as the first rule. Rewrite the "Values are literal text" paragraph: a line whose first character is `#` or whose first two are `//` lexes as `comment` (the first alternative of `line`, so column 0 only); every other line lexes as `structure` or `data` on its own characters, but a line inside an open text value is that value's text whatever it lexes as (§5.1). Delete the no-uppercase-key paragraph. State that `indent` is U+0020 only and that a line consisting only of spaces and tabs is blank (§4.4). |
| §4.2 | Rule 3: drop the `key: \tv` sentence; a value cannot begin with a tab (the separator absorbs it; in block form it would be a tab in indentation). Rule 4: "number of leading U+0020 characters; no other character is indentation". Rule 5: "list items included". Replace the three-space invalid example with the one-space dedent and show the three-space line as a text continuation (R-06). |
| §4.3 | **Rewrite, do not delete** (principal ruling 2026-09-24; FR-007, D23 as revised). A line whose first character, at column 0 with no indentation, is `#`, or whose first two characters are `//`, is a comment, whatever follows. It is skipped as if it were not in the document, anywhere: between entries, before a document's or block's first line, and between two lines of an open text value, where it is not a line of the value and not a paragraph break (blank lines on either side still count one for one, §5.1). An indented `#`/`//` line is text (a continuation of an open value, a block's first line, or text at a container's level, §6.4), and so is any `#`/`//` after `key:`, `-`, or inside a value. Only U+0020 is indentation, so a NBSP-led `# x` is text; §9.0 strips a BOM at index 0 before lexing, so a BOM-led first line can be a comment, and a BOM anywhere else is content. Keep the `key: value  # …` and `- item # not a comment` examples and the `#tag: value` → `""` example (all still true). Replace the "Comments must be on their own line" sentence with "Comments must be on their own line and start at column 0". Add Output-bearing examples: `a:\n# note\n  b: 1` → `{"a": {"b": "1"}}`; `k:\n  a\n# note\n  b` → `{"k": "a\nb"}`; `k:\n  a\n  # note\n  b` → `{"k": "a\n# note\nb"}`; `server: # prod\n  host: x` → `{"server": "# prod\nhost: x"}`. |
| §4.4 | Blank = only spaces and tabs (a NBSP-only line is text). Blank lines between structure are inert; inside a value they are paragraph breaks (§5.1). Keep the example. |
| §4.5 | Replace the pattern with `[a-z][a-z0-9_-]*`: the whole rule. Delete the no-uppercase rationale, the `\s`/White_Space paragraph, the `#`/`//` exception (a key matching the pattern cannot start with either), and the residual-hazard paragraph's uppercase framing (a lowercase `word: ` line is still a key where structure is lexed: a block's first line, an inline list value, a mapping's level). Replace the key-examples block with valid and invalid keys; `Été: chaud` and `- Listen: …` stay as text examples. |
| §4.6 | Keep the `# Inline value` etc. label lines: they are at column 0, so they are comments and every Output stays true (the pre-ruling plan removed them). |
| §4.6.1 | Add: VT, FF, NEL, U+2028, NBSP and every non-U+0020 character at the start of a line are content, not indentation. |
| §5.1 | Rule 4 (comments) rewritten: a column-0 comment line inside a multi-line value is skipped, is not part of the value, is not a paragraph break, and does not end the value; an indented `#`/`//` continuation line is text and is kept (`- tag line\n  #winning` → `["tag line\n#winning"]`). The "unrepresentable by `dumps`" sentence goes, except for a root scalar (§11.2.1 item 9). Rule 5 rewritten: a blank line between two lines of the same value is an empty line of the value, one per physical line; an inline value's text counts as its first line (R-04); blank lines before a block value's first line or after its last are inert. Rule 6 rewritten: structure is lexed only at a block's first line and inline; once a value is text, every line at or past its baseline is text; a root document whose first line is text is text throughout. Add the US1 1, 3, 14, 16 examples. |
| §5.3 | Keep the baseline text. Replace "a line that syntactically parses as its own structure is never a TextLeaf continuation" and the `note: hello\n  more: text` ERROR example with its new output `{"note": "hello\nmore: text"}`. Keep `key: a\nb` (ERROR). Add the root `  hello` examples if not already Output-bearing. |
| §6 intro / §6.1 | Add the indentless-sequence ERROR example (`k:\n- a`) with its hint. |
| §6.2 | Unchanged rule; add the nested-vs-sibling pair (`- server:\n    host: x` vs `- server:\n  host: x`). State that a column is a count of code points, so a tab after `-` counts as one column: `-\tk: v\n  j: w` is two siblings, and `-\tk: v\n        j: w` joins `v` (Output-bearing examples for both). |
| §6.4 | Keep; add that an **indented** `#`/`//` line at a container's level is text and errors like `plain` (`a:\n  b: 1\n  # note` raises), while a column-0 one is a comment (`a: 1\n# note\nb: 2` → `{"a": "1", "b": "2"}`). |
| §7.2 | Keep the mapping/list asymmetry. Add: at a continuation position a `- ` line is text (§5.1). |
| §7.4 | Unchanged in substance: "An empty document, or one with only comment and blank lines, is `""`." Say "column-0 comment lines"; an indented `#` line is text, so `# one\n  # two` is `"  # two"`. |
| §7.5 (fenced-example limit) | A fenced example cannot end a line with a space or tab: the `trailing-whitespace` pre-commit hook strips it, so `a:\t` + newline + `  b: 1` (US2-4) and a whitespace-only blank line inside a value (R-03) are stated in prose or inline code with escapes, never as an Output-bearing fenced block. A tab inside a line (`key:\tv`, `-\tk: v`) survives the hook, as the three tabs in today's spec do (red team outer iteration 10). |
| §7.5 | `ws` is spaces or tabs. `key:\tvalue` → `{"key": "value"}`; `-\tvalue` → `["value"]`; `key: \tv` → `{"key": "v"}`; a bare marker followed only by spaces or tabs is the bare marker (R-11). A separator tab counts as one column (§6.2). |
| §7.6 | Table: `Invalid: value`, `key:\tv`, `key:value` rows updated (`key:\tv` is now a mapping). Replace the "every line is lexed independently" subsection with the text-context rule: `a: Note\n  warning: do not touch` → `{"a": "Note\nwarning: do not touch"}` (was ERROR). |
| §8.1 | Unchanged example; it still raises. |
| §8.3 | Output line matches the code: `ERROR: DuplicateKeyError: Duplicate key 'key' (first defined at line 1)` (Contract 03 makes the code produce it; D32, syml-cjk2.16). |
| §8.4 | Last paragraph: a tab after `-`/`:` is separator whitespace (§7.5), not this error. |
| §8.5, §13.4 | Limits are recommendations; `DocumentLimitError` is the name for an implementation that enforces them; `syml` enforces none (FR-017). |
| §9.1 | Step 3: comment classification applies only at column 0 (the `comment` alternative of `line`); comment and blank lines are skipped by the builder, and paragraph breaks are recovered from line positions by counting the blank lines between two lines of a value, never the comment lines (§5.1). |
| §9.3 | KeyValue row unchanged in text (`level > keyvalue.level`), now true of the code. TextLeaf paragraph: add the text-context rule (a candidate at or past the threshold is accepted as text whatever it lexed as). Delete "`key: \t` has the one-character value `\t`" (R-11). |
| §10.2 | Add R-09's BOM sentence. State the `str(error)` form (FR-011) and that its rendered filename and line escape non-printable characters (`\xa0`, `\x1b`, `\t`, `\n`, lone surrogates) while `message` and `line_text` stay raw (Contract 03). |
| §11.1 | "an empty document or a document containing only column-0 comment and blank lines" (the 1.0 wording, with "column-0" added). |
| §11.2.1 | Rewrite to Contract 04's nine items (item 9: a root scalar with any line that begins with `#` or `//`, which would read back as a comment; the one comment clause that survives) (item 2 including its later-line clause: more than 32 leading `- ` markers, a fixed count); B/C/D/G letters kept for references; add the inline-first spelling as a v1.x candidate (R-05). The opening sentence ("a conforming `dumps` has exactly one way to write each string … such that `loads(dumps(x)) == x`") is false under D21, because the L1 family has an inline-first spelling `dumps` does not use: say instead that `dumps` writes each string in one canonical layout, and name the three load-only families (Contract 04 L1–L3) as values `loads` can return that `dumps` refuses (red team outer iteration 7). The "MUST raise rather than emit text that would not read back" guarantee covers a value's text; say that structural depth is §13.4's cliff and `dumps` does not check it (a list nested past about 120 levels is written as one `- - …` line that `loads` cannot read; red team outer iteration 8, plan open question 9, ruled "document only" by the principal on 2026-09-24). |
| US3 narrative (spec.md, not §11.2.1) | **Applied in `spec.md` by red team outer iteration 3; the spec leaf only checks it still holds.** The closing sentence "the residual unrepresentable set is exactly the values that have no spelling at all" is false by R-05's own finding (the inline-first mapping family, `{"k": "a: 1\nb"}`, has a spelling but stays refused). Reword to something the code actually satisfies, e.g. "the residual unrepresentable set shrinks to the nine families FR-006 names, one of which (a structure-shaped first line at a mapping position) keeps a spelling `dumps` still declines to use." This is a spec-leaf obligation, not a code obligation: FR-006/`dumps` are unchanged by it. The rewording must also not claim that every value `loads` returns can be written: name all three load-only families (Contract 04 L1–L3: the inline-first mapping spelling; rule D's control characters that §4.6.1 reads verbatim; and a later line with more than 32 leading `- ` markers, red team outer iteration 7), matching §11.2.1's row above. Record the red team's verdict (plan open question 3) in spec.md's Clarifications. |
| FR-016, US4 scenario 4 (spec.md) | **Applied in `spec.md` by red team outer iteration 3.** Both said the comments item warns that files with `#` lines are "loud"/"change meaning". Reword so the obligation matches the behaviour: a `#`/`//` line that is the first line of a document or block makes that document or block one string, silently; a later one at a container's level raises. Record the correction in spec.md's Clarifications (red team pass 1, plan open question 7). **Superseded by the principal's ruling of 2026-09-24, applied in `spec.md`:** a column-0 `#`/`//` line is a comment, so the silent and raising cases are now only the **indented** ones, plus `#` after a key or marker. |
| §11.2.3 | Keys: exactly `[a-z][a-z0-9_-]*`; everything else raises. Delete the quoted-key/`#` v1.2 note or reduce it to the quoted-key candidate. |
| §11.3 | Contract 05 wording: add `EncodingError`; `DocumentLimitError` reserved. |
| §12.1 | Keep the `# Application configuration` line: it is a column-0 comment, so the example still loads as a mapping (the pre-ruling plan removed it). |
| §13.1–§13.3 | Remove White_Space-in-key references; reduce comment references to the column-0 rule; keep §13.3's LF-only line boundary and its BOM scope (index 0 only), which decides whether a first-line `#` after a BOM is a comment. |
| §13.4 | Name the second recursion shape next to the nesting cliff: a line of many `- ` markers raises `RecursionError` from the per-line lex even inside a text value (§5.1), and `dumps` refuses to write a later line with more than 32 (§11.2.1), a fixed bound chosen well under the cliff because the cliff moves with the caller's stack depth. Figures from R-17 measurement 5, including the cliff at a shallow stack and with 500 frames already in use. Also state that `dumps` writes a nested list inline (`- - x`), so its output for nesting deeper than measurement 6's figure does not load, and that this depth is lower than the block-nesting cliff (red team outer iteration 8). |
| §14 | Rewrite the 1.0 row's comment (column 0 only, skipped anywhere, an indented `#` is text), key, blank-line, D13, and tab clauses to the revised rules (keep it one row). |

## B. `SYML-SPEC-REVIEW.md` (spec leaf)

Add a second amendment block after the D18/D19 one, dated 2026-09-24, naming
the break-test campaign (`syml-xreq`) and the principal's rulings. Append six
rows to the decisions table; each carries the alternative not taken and a
breaking-change note (FR-016):

| # | Decision (summary) | Alternative not taken | Supersedes | Breaking change |
| --- | --- | --- | --- | --- |
| D20 | A key is exactly `[a-z][a-z0-9_-]*`, preceded only by indentation spaces; any other would-be key line is text; `dumps` refuses other keys. | Keep D19's "no `Lu`/`Lt`" rule plus a leading-bracket/quote exclusion (`syml-xreq.16` option b). | D15, D19 | `Name:`, `firstName:`, `URL:`, `1:`, `e.mail:`, `名前:` stop being keys. Inside a list item the effect is asymmetric: a non-pattern **first** key makes the whole record one string with no error (`- containerPort: 80\n  protocol: TCP` → `["containerPort: 80\nprotocol: TCP"]`, raised in 1.0), while a non-pattern later key raises with hint (a) (red team outer iteration 5). |
| D21 | Values are just text: structure is lexed at a block's first line and inline only; once a value is text, every line at or past its baseline is text until a line below it; a root document whose first line is text is text throughout. | Keep per-line lexing and add an error hint (`syml-xreq.22` option a). | D13 | Deeper structure-shaped lines after a text value join it; a line indented past a sibling that holds an inline value is absorbed silently (R-06). Lexing still runs first, so a long `- - - …` line still raises `RecursionError` inside a text value; an iterative list-marker rule that would lift this is a 1.x candidate. |
| D22 | A blank line between two lines of the same value is an empty line of that value, one per physical line; blank lines before a value's first line, after its last, or between items/keys are inert; `dumps` writes paragraph breaks. | An explicit paragraph marker line (`syml-xreq.15` option c). | D12 | `k:\n  a\n\n  b` was `"a\nb"`, is `"a\n\nb"`. |
| D23 | Comments are column-0 only (principal ruling 2026-09-24, superseding the "no comments" reading of `syml-xreq.21`): a line whose first character, with no indentation, is `#`, or whose first two characters are `//`, is a comment, skipped as if absent anywhere in the document, including between two lines of an open value (not a paragraph break). Every indented `#`/`//` line and every `#` after a key or marker is text. | Remove comments entirely (the first reading of the `syml-xreq.21` ruling; overruled because its "all loud" premise was false); `#` only; comments only between structure entries (R-18). | §4.3's "a line beginning with `#` or `//` is always a comment, at any indentation", M6's skip-the-continuation fix, B9's exception | Column-0 comment lines, file headers included, keep working. An **indented** `#`/`//` line changes meaning: inside a value it is kept as text (`- tag line\n  #winning` → `["tag line\n#winning"]`, where 1.0 dropped it); at a container's level after its first entry it raises; and, **silently**, as the first line of a block it makes that block one string (`a:\n  # s\n  b: 1` → `{"a": "# s\nb: 1"}`). And, **silently one level down**, a `#`/`//` after `key:` or `-` (YAML's trailing comment) is that key's or item's text value and takes in the block under it (`server: # prod\n  host: x` → `{"server": "# prod\nhost: x"}`, raised in 1.0; red team outer iteration 5). A root scalar with a line that begins with `#` or `//` is unrepresentable by `dumps` (§11.2.1 item 9). |
| D24 | A tab is separator whitespace after `key:` and `-` (`ws = [ \t]+`); a marker followed only by spaces/tabs is bare; a tab in indentation still raises. A separator tab counts as one column for §6.2's sibling column. | Make a post-marker tab an error (v1.2 candidate 4). | D5 | `k:\tv` was `"k:\tv"`, is `{"k": "v"}`; `k: \tv` was `{"k": "\tv"}`, is `{"k": "v"}`. After `-\tk: v`, a sibling key goes at column 2; a line an editor shows aligned under `k` at a tab stop joins `v` silently. |
| D25 | Children are strictly deeper than their parent, list items included; the YAML indentless sequence is an error with a hint. §6.2's `- key:` sibling-column rule stands. | Keep the undocumented carve-out and add a KeyValue row to §9.3 (`syml-xreq.3` recommendation). | — (restores §4.2 rule 5 / §9.3 over code) | `k:\n- a` was `{"k": ["a"]}`, is `OutOfContextNodeError`. |

Annotate in place (the D18 precedent: a bold "Superseded by Dnn (2026-09-24)"
lead-in, text otherwise left): D5 → D24, D12 → D22, D13 → D21, D15 → D20,
D19 → D20. Annotate M6 ("closed by D23: an indented `#`/`//` continuation is text; a column-0 one is a comment, skipped by design") and M20 ("closed by D22"), M21 ("moot under D20"),
M24 ("changed by D21"), and B9 ("moot under D20/D23"). Record in the
verification section that the spec's examples were re-run against the shipped
code (the SC-005 test) rather than a scratch harness.

## C. `CHANGELOG.md` (release leaf)

The 1.0.0 entry stays one entry. Corrections (FR-016):

| Item | Correction |
| --- | --- |
| 4 | Rewrite for D20: the key pattern, `Name: x` / `firstName: x` / `URL: x` / `名前: x` are text; the D19 General_Category text goes. |
| 7 | True once FR-005 lands; keep, add `  hello\nworld` → `'  hello\nworld'`. |
| 9 | True once FR-013 lands; add `str(e)` → `file:line:col: message` plus the line. |
| 10 | Replace the `Source.from_node` signature claim with the real one `(pnode, filename=None)`. |
| 11 | "a `str` or `os.PathLike` `file_obj.name`" (true once FR-017 lands); `loads(bytes)` → `TypeError`. |
| 12 | Drop the `SymlParser`-takes-a-`Document` claim; rewrite the `dumps` paragraph to Contract 04's set; `dumps('')` is `''`. |
| 13 | State the measured figures (R-17), including that `parse()` can succeed where `as_data()` raises. |
| 16 | Keep only what is true: `level` is the node's own column; `set_level`, `IndentNode`, `Comment`, and `SymlNode.comments` are gone; `syml.utils` is deleted. Delete the `doc`-argument, required-`source`, `KeyLeafNode.key`-removed, and no-`pnode` claims. |
| 17 | True once FR-010 lands; add the indentless-sequence line (`k:\n- a` now raises, with a hint). |

New breaking-change items, one per decision (FR-016): D20 keys (with the
list-item asymmetry: a non-pattern first key silently makes the record one
string, a non-pattern later key raises with a hint); D21 values
are text throughout (with the silent-absorption note, and the general
migration check: every `key:` or `-` followed by separator whitespace and a
non-empty inline value, with a deeper block under it whose first line 1.0
lexed as a key or list item, now loads that block as part of the inline
value's string where 1.0 raised; the D23 item's `#`
search is the commonest instance, and an invisible inline value is the
hardest: `server: \xa0` over a `host:` block reads as a bare section but
loads as `{"server": "\xa0\nhost: a"}`, red team outer iteration 6); D22 paragraph breaks
kept; D23 comments at column 0 only (principal ruling 2026-09-24), stating
what still works and what changes for any third-party `.syml` file with `#`
lines. What still works: a `#` or `//` line that starts at column 0 is a
comment wherever it appears, file headers and section notes included, and
between two lines of a value it is skipped without adding a blank line. What
changes: an **indented** `#`/`//` line is now text, so inside a value it is
kept (1.0 dropped it), after a container's first entry it raises, and as the
first line of a block it silently turns that block into one string; and a
`#`/`//` after `key:` or `-` (`server: # prod`) silently makes the block
under it part of that key's string. The item says how to check: search the
file for every **indented** line whose first non-space characters are `#`
or `//`, and every `key:` or `-` followed by separator whitespace and `#` or
`//`. A hit of the first kind changes meaning (the fix is to move the
comment to column 0); a hit of the second kind changes meaning only when a
deeper block follows it (`k: # x` alone was already the string `"# x"` in
1.0), so the item says to check what that key loads to. A top-level
`isinstance(loads(text), dict)` check is **not** the advice (red team outer
iteration 5): it passes for `server: # prod\n  host: x`, whose damage is one
level down. The "loud" wording of the ruling is not
used; D24 tab as separator (with the one-column note) (`k:\tv`, `k: \tv`); D25 indentless sequences
rejected. One more item for the only-U+0020-indentation fix (`\xa0k: v` is
text; NBSP, VT, FF, NEL, U+2028 at a line start are content; a document or
block whose first line starts with a NBSP, as indentation pasted from a web
page does, silently loads as one string, red team outer iteration 2; and a
NBSP, U+200B, or U+3000 left after `key: ` or `- ` is an inline value that
silently takes in the block under it, red team outer iteration 6; and a line
holding only a NBSP, form feed, or other non-space character is no longer a
blank line: indented under a value it silently joins that value, so
`k: v\n \xa0\nj: w` loads `k` as `"v\n\xa0"` where 1.0 gave `"v"`, and at a
container's column it raises, red team outer iteration 8). The D24
item states the converse edge: only a space or a tab separates; a NBSP after
`key:` (macOS Option-Space, pasted text) makes the line text, so
`name:\xa0app\nport: 80` is one string where 1.0 raised at line 2 (red team
outer iteration 3).

Item 25 (D26, `syml-cjk2.10`): a third `OutOfContextNodeError` hint, (c)
missing space after a marker — `key:8080` or a bare `-8080` reads as a
would-be key or list marker with no separator, and the hint names it. Item
26 (D27, `syml-cjk2.11`): two more hints — (d) an indented comment line
that would have been a comment at column 0, and (e) a mid-file document
marker (`---`/`...`) that 1.0 never treated specially. Both are described
in Contract 03 §Hints. README change: D26 adds "Coming from YAML" bullet 7,
the hint (c) item itself (§D item 7 below); D27 edits bullets 1 and 3,
adding "with a hint" to bullet 1's indented-comment raise and "a raise
there gets a hint too" to bullet 3's mid-file document-marker raise (§D
items 1, 3 below) — the error section proper still does not enumerate
individual hints.

Recursion measurement method (R-17): at the default recursion limit, bisect
the largest depth that loads for (1) `k0:\n  k1:\n    …` with no trailing
line, (2) the same plus a trailing `z: 1` at column 0, (3) `- - … - x` on one
line, (4) `dumps` of a nested dict, (5) the same `- ` chain as a continuation
line of a text value (`k:\n  a\n  - - … - x`), confirming it raises where (3)
does and that `dumps` refuses the value that would write it (Contract 04
item 2); (6) `dumps` of a nested list (`[[…]]`, written as one `- - … x`
line) and of a list of one-key dicts, bisected on whether `loads` reads the
output, at a shallow stack and with 500 frames already in use (red team
outer iteration 8 measured 121 / 58 and 248 / 123 on the planning spike,
against 496 / 246 for nested dicts); also record the depth where `parse()`
succeeds but `.as_data()` raises.

D34 (`syml-cjk2.5`, refined by `syml-cjk2.19`, break-testing round 2 lane
3): item 27, extending Contract 03 §Bounded rendering (`syml-s9p9.9`/`.14`,
already itemized above under recursion measurement's neighbor obligations)
to a hostile `filename`, via `_truncated_filename_window(filename,
width=1024)`: a filename up to 1024 code points passes through whole, and a
longer one is windowed from its **tail** — `'…'` plus its last 1023 code
points — so a path's basename always survives. This replaces
`syml-cjk2.5`'s original 80-code-point head-centered window, which cut the
basename off any real-world absolute path longer than 80 characters
(routine for CI runner paths), silently making `str(e)`'s `path:line:col`
form unclickable. No README change — the README never documented the
bounded-rendering length cap itself, only the hints it now covers.

Bug-fix item, no D-number (`syml-cjk2.6`, break-testing round 2 lane 3):
item 28, `load()` on an object with no `read()` method (e.g. `None`, a bare
`str`, or any other non-file object) now raises `TypeError` naming the
received type instead of letting a bare `AttributeError` escape, matching
`loads`'s own `TypeError` for a non-`str` argument and `load`'s existing
`TypeError` for a `read()` result of the wrong type (Contract 05 §Behaviour).
No README change — the README's `load()` example already shows only the
happy path.

Bug-fix item, no D-number (`syml-cjk2.9`, break-testing round 2 lane 5):
item 29, Contract 04 item 2's 32-marker guard no longer counts a trailing
dash followed by non-whitespace text (e.g. `-42`) as a marker, so exactly
32 real markers followed by such a dash writes and round-trips instead of
raising `UnrepresentableValueError`. No README change — the README does
not document the 32-marker bound.

D30 (`syml-cjk2.14`, break-testing round 2 lane 4): item 30, `str(e)` for
`UnrepresentableValueError` and the `dumps` `TypeError` is the message
alone, never a tuple repr of `.args` — the pre-fix bug (`str(e)` on
`dumps({"a": {"b": ["x", 1]}})` rendered
`('...', 1)`) — and the message now names the offending value's data path
in Python subscript form, e.g. `at ['a']['b'][1]`, omitted for a root
value. `UnrepresentableValueError` gains a public `.path` attribute
(`tuple[str | int, ...]`, `()` at the root); the `dumps` `TypeError` stays
a plain builtin `TypeError`, message only, no `.path`, no new subclass
(Contract 04 §Error text and the data path). The whole message is bounded,
not only the path clause (`syml-cjk2.18`, refined by `syml-cjk2.25`): a
hostile mapping key or scalar value (e.g. a multi-megabyte string, or a
huge non-`str` key/value such as a 300,000-element tuple) is windowed
through `_truncated_window(..., center=0)` before interpolating, yielding a
bounded `str(e)` on its own, not only in combination with a long path
(Contract 04 §Bounded rendering). No README change — the README does not
document either error's message shape.

D31 (`syml-cjk2.15`, refined by `syml-cjk2.21`, break-testing round 2 lane
4): item 31, `EncodingError`'s message names the first offending byte and
says UTF-8 (`Invalid UTF-8 (byte 0x{XX}); save the file as UTF-8`), and
names the actual codec instead when a caller-supplied text stream in a
non-UTF-8 codec fails to decode (`Invalid {codec} (byte 0x{XX})`, no
UTF-8-specific advice), replacing the pre-fix `Invalid encoding` (Contract
03 §Messages). For a charmap-based codec (`cp1252`, `cp437`, the `latin-*`
family), the named codec was still wrong — Python's own
`UnicodeDecodeError.encoding` reports the literal `'charmap'` for all of
them, not the codec the caller chose — so `load()` now prefers the
stream's own `encoding` attribute over `err.encoding` when naming the
codec, falling back to `err.encoding` only for bytes input, which has no
stream to ask (`syml-cjk2.26`). No README change — the README does not
document `EncodingError`'s message shape.

D32 (`syml-cjk2.16`, break-testing round 2 lane 4): item 32,
`DuplicateKeyError`'s message names where the key first appeared —
`Duplicate key 'a' (first defined at line N)` — replacing the pre-fix bare
`Duplicate key 'a'`; `.first_position` is unchanged, only the message
gained the clause (Contract 03 §Messages, §8.3). No README change — the
README does not quote `DuplicateKeyError`'s message.

D33 (`syml-cjk2.17`, break-testing round 2 lane 1): item 33, `str(e)`'s
excerpt line no longer misaligns by one character on a long line 1 of a
BOM-led document: `__str__` now centres its window on `.position.column`
minus the BOM offset instead of the raw column, matching the equivalent
non-BOM document's rendering; `.position` and `.line_text` are unchanged
(Contract 03 §Placement). No README change — the README does not show a
BOM-led excerpt example.

D35 (`syml-cjk2.20`, break-testing round 2 lane 1, amending D26): item 34,
hint (c) (item 25) no longer fires on a URL value: its key alternative
excludes `://` immediately after the colon
(`^[a-z][a-z0-9_-]*:(?!//)\S`), on both the failing line and the look-back,
so a legitimate `scheme://` value (`http://example.com`, and §8's own
`url: https://example.com:8080/path`) never earns "a key or list marker
needs a space after it" — advice that would turn a valid value into a key
(Contract 03 §Hints). README change: "Coming from YAML" bullet 7 (item
25's README addition) gains the URL-exemption sentence (§D item 7 below).

Bug-fix item, no D-number, appended out of decision order (`syml-cjk2.13`,
break-testing round 2 lane 4; the JUDGMENT this item resolves, D29): item
35, `dumps`'s unrepresentable-value messages for Contract 04 items 5 and 6
change wording only — item 5's message is `contains a non-empty
whitespace-only line`, replacing the pre-fix `contains a blank or
whitespace-only line` (which used "blank" for a non-empty line, reading as
though a paragraph break were refused); item 6 splits into
`begins with a blank line` / `ends with a trailing newline`, naming which
end caused the refusal, replacing one shared pre-fix message (Contract 04
§Unrepresentable set, items 5 and 6). No README change — the README does
not quote either message.

Packaging item, no D-number (`syml-6h0t`, the 2026-09-26 install-test pass
on the built artifacts): item 36, `src/syml/py.typed` ships in the wheel
(PEP 561), the `License :: OSI Approved :: MIT License` classifier is
removed because PyPI rejects it alongside `License-Expression` (PEP 639),
and the Python 3.13 and 3.14 classifiers are added after the wheel and
sdist install and pass the smoke check on both. Guarded by
`scripts/smoke-install.sh` (`just smoke-install`), which the release
workflow runs before upload. No README change.

## D. `README.md` (release leaf)

1. **"Coming from YAML"** section, in this order, each with the SYML spelling
   beside it (FR-015, US4 scenario 5):
   1. Comments only at column 0: a line that starts with `#` or `//`, with
      no indentation, is a comment, anywhere in the file. An indented
      `# note` is text: as the first line of a block it makes that block one
      string, with no error, and after a block's first entry it raises (with
      a hint, D27). A trailing comment is text too (`port: 80 # default`
      keeps `# default`), and after a key it takes in the block under it
      (`server: # prod` makes the block under it part of `server`'s string).
   2. No block-scalar indicators: `|` and `>` are literal; indent the lines
      under the key instead.
   3. No document markers: `---` and `...` are text (a document starting with
      one is a single string; mid-file, a raise there also gets a hint,
      D27).
   4. No quoting: `"x"` keeps its quotation marks.
   5. `null`, `true`, `123`, `~`, `[a, b]`, `{a: 1}` are plain strings.
   6. Keys are `[a-z][a-z0-9_-]*`: `Name:`, `firstName:`, `URL:` are text, and
      a block of them (`env:\n  HOME: /h`) is one text value; so is a whole
      file whose first line is one (`Name: app\nport: 80` is a string), and
      so is a list item whose first key is one
      (`- containerPort: 80\n  protocol: TCP` is one string). A bad key
      after a good one raises with a hint.
   7. A key or list marker needs a space after it (D26): `port:8080` (no
      space after the colon) is not a key — it's text, so it silently makes
      the whole document, or the whole block it's in, one string; same for
      `-b` in a list. When it raises instead, the error now includes a hint.
      A URL value (`http://example.com`) is exempt: the hint never fires on
      a `scheme://` value (D35).
   8. `- key:` sets a sibling column: `- server:\n  host: x` is two siblings;
      `- server:\n    host: x` nests (show both). Use a space after `-`:
      a tab there counts as one column.
   9. A blank line inside a value is a paragraph break.
   10. Trailing whitespace on a value is kept, and an over-indented line
       joins the value above it (D28): `host: db1   ` keeps its trailing
       spaces; a YAML-style sub-bullet like `- Budget review\n    - Q3
       numbers` is one item, not two.
2. A **`Source`** paragraph with Contract 05's three facts (FR-014).
3. Any README example that uses an indented comment line, a key outside
   `[a-z][a-z0-9_-]*` (uppercase, camelCase, or punctuation: the lead
   example's `booleans?:` raises `OutOfContextNodeError` under D20), or an
   indentless list is fixed. The lead example's key becomes `booleans:` in
   both the input and the printed result; that edit lands in the **grammar
   leaf**, with the two `tests/test_parsers.py` README tests that mirror it
   (red team outer iteration 4, plan § Edge Cases).
4. The **"Serializing"** paragraph is rewritten to what ships (red team outer
   iteration 4): the output writes a paragraph break as an empty line (not
   "no blank lines"); a root scalar keeps its leading spaces; `dumps` accepts
   `Source` keys and scalars; and the `UnrepresentableValueError` list is
   Contract 04's nine items in plain words (no "leading space", "blank or
   `#`-initial or structure-shaped line inside a multi-line value", or
   "uppercase letter" wording; the one `#` refusal left is a root scalar
   with a line that begins with `#` or `//`), with the key rule stated as
   the pattern.

## E. Other text

- `CLAUDE.md` § Architecture: every line lexes as `comment / (indent
  (structure / data))` under `document = (line "\n")* line?`, and the
  visitor drops a column-0 comment line; the tree builder's text context
  (Contract 02). § Spec vs. implementation: "D1–D25".
- `specs/002-syml-language-revision/reference/README.md`: the
  `doc05c`/`doc05d` note is corrected in the plan commit (R-06).
- `specs/readme.md` (the Pin): unchanged unless the implementation adds a
  keyword worth indexing.

## F. The tag (release leaf, last)

`pyproject.toml` stays `1.0.0`. No `1.0.0` tag exists yet, locally or on
`origin` (checked at `3bda444`; the spec's "unpushed tag" is a tag still to be
created). After every other leaf is closed, the gates are green, and the
branch is merged to `master`: create an annotated `1.0.0` tag on the merge
commit, `git push origin 1.0.0`, and verify with `git ls-remote --tags origin`
(US4 scenario 7). No PyPI upload.

**US4 scenario 7 runs outside `just acceptance`** (red team outer iteration
10). CI runs `just acceptance` on every push, and the tag goes on the merge
commit only after that commit is pushed, so a tag check inside the normal
acceptance run fails the merge commit's own CI job and ties every later run
to the network and the remote's state. The US13 feature tags scenario 7
`@release`; `pyproject.toml` registers the `release` marker; `just
acceptance` becomes `-m "acceptance and not release"`; a new `just
release-check` recipe runs `-m release`. The release leaf runs it by hand
after `git push origin 1.0.0` and records the output in its close reason.
The binding reads the peeled SHA (`refs/tags/1.0.0^{}` in `git ls-remote
--tags origin`; an annotated tag's own ref names the tag object) and asserts
it equals `git rev-parse 1.0.0^{commit}` and is an ancestor of, or equal to,
`HEAD`, never that it equals `HEAD`.

## Test obligations

1. `tests/test_spec_examples.py` passes over the edited spec with the new
   minimum count (SC-005, US4 scenario 1). **The oracle checks an ERROR
   line's message, not only its class** (red team outer iteration 10): today
   the extractor keeps only the name before the first `:` after `ERROR:` and
   the test uses `pytest.raises`, which also accepts a subclass, so §8.3's
   `Duplicate key 'key'` and §6.1's hint text would never be compared with
   the code. When the code span has text after `ERROR: <Class>:`, the test
   asserts `type(e) is <Class>` and that the text equals `e.message` (the
   oracle passes no filename, so there is no prefix); a span that names only
   a class keeps the class check, made exact. The spec leaf lands this
   extractor change with the `PENDING` table, whose `(source, stated output)`
   key includes the message text.
2. The grammar-identity test (Contract 01).
3. The §11.3-vs-exports test (Contract 05).
4. `tests/acceptance/test_us09_release_readiness.py`'s CHANGELOG assertions
   (built for 001) are updated for the rewritten items rather than deleted.
5. A US13 acceptance scenario reads the README section headings and asserts
   the ten items in order.
6. A unit test reads `README.md`, extracts the lead example's document and
   its printed result (the first two fenced `python` blocks), and asserts
   `loads(document) == ast.literal_eval(result)`, so the README's first
   example cannot again drift from the parser. It replaces the two
   hand-copied `test_parsers.py` README tests or sits beside them (red team
   outer iteration 4).
