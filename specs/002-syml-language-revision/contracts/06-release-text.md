# Contract 06 — Release Text: Specification, Decision Record, Changelog, README, Tag

**Requirements**: FR-015, FR-016, FR-017 (§11.3 half), FR-018; US4 | **Findings closed**: `syml-xreq.8`, `.9` (text half), `.10` (docs), `.24`, `.3`/`.17`/`.20` (README halves) | **Research**: R-02, R-05, R-06, R-09, R-10, R-11, R-17

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
| §2 | Drop "A **comment**" from the line kinds. §2.1's unlabelled block uses `#` labels: replace them with prose labels outside the block (or three blocks). |
| §4.1 | Print Contract 01's grammar, with `eol`'s regex as the raw literal `~r"\Z"` (the current §4.1 prints `~"\Z"`, which does not load under the repository's `error::SyntaxWarning` policy; Contract 01) and `document` as the first rule. Rewrite the "Values are literal text" paragraph: every line lexes as `structure` or `data` on its own characters, but a line inside an open text value is that value's text whatever it lexes as (§5.1). Delete the no-uppercase-key paragraph. State that `indent` is U+0020 only and that a line consisting only of spaces and tabs is blank (§4.4). |
| §4.2 | Rule 3: drop the `key: \tv` sentence; a value cannot begin with a tab (the separator absorbs it; in block form it would be a tab in indentation). Rule 4: "number of leading U+0020 characters; no other character is indentation". Rule 5: "list items included". Replace the three-space invalid example with the one-space dedent and show the three-space line as a text continuation (R-06). |
| §4.3 | **Delete.** Renumber nothing (keep §4.4 onward) or leave "§4.3 (removed in 1.0: SYML has no comments; see D23)" so external references resolve. Choose the stub. |
| §4.4 | Blank = only spaces and tabs (a NBSP-only line is text). Blank lines between structure are inert; inside a value they are paragraph breaks (§5.1). Keep the example. |
| §4.5 | Replace the pattern with `[a-z][a-z0-9_-]*`: the whole rule. Delete the no-uppercase rationale, the `\s`/White_Space paragraph, the `#`/`//` exception, and the residual-hazard paragraph's uppercase framing (a lowercase `word: ` line is still a key where structure is lexed: a block's first line, an inline list value, a mapping's level). Replace the key-examples block with valid and invalid keys; `Été: chaud` and `- Listen: …` stay as text examples. |
| §4.6 | Remove the `# Inline value` etc. lines from the four blocks; label them in prose. |
| §4.6.1 | Add: VT, FF, NEL, U+2028, NBSP and every non-U+0020 character at the start of a line are content, not indentation. |
| §5.1 | Rule 4 (comments) deleted. Rule 5 rewritten: a blank line between two lines of the same value is an empty line of the value, one per physical line; an inline value's text counts as its first line (R-04); blank lines before a block value's first line or after its last are inert. Rule 6 rewritten: structure is lexed only at a block's first line and inline; once a value is text, every line at or past its baseline is text; a root document whose first line is text is text throughout. Add the US1 1, 3, 14, 16 examples. |
| §5.3 | Keep the baseline text. Replace "a line that syntactically parses as its own structure is never a TextLeaf continuation" and the `note: hello\n  more: text` ERROR example with its new output `{"note": "hello\nmore: text"}`. Keep `key: a\nb` (ERROR). Add the root `  hello` examples if not already Output-bearing. |
| §6 intro / §6.1 | Add the indentless-sequence ERROR example (`k:\n- a`) with its hint. |
| §6.2 | Unchanged rule; add the nested-vs-sibling pair (`- server:\n    host: x` vs `- server:\n  host: x`). State that a column is a count of code points, so a tab after `-` counts as one column: `-\tk: v\n  j: w` is two siblings, and `-\tk: v\n        j: w` joins `v` (Output-bearing examples for both). |
| §6.4 | Keep; add that a `#`/`//` line at a container's level is text and errors like `plain`. |
| §7.2 | Keep the mapping/list asymmetry. Add: at a continuation position a `- ` line is text (§5.1). |
| §7.4 | "An empty document, or one with only blank lines, is `""`." A document of former comment lines is a root scalar. |
| §7.5 | `ws` is spaces or tabs. `key:\tvalue` → `{"key": "value"}`; `-\tvalue` → `["value"]`; `key: \tv` → `{"key": "v"}`; a bare marker followed only by spaces or tabs is the bare marker (R-11). A separator tab counts as one column (§6.2). |
| §7.6 | Table: `Invalid: value`, `key:\tv`, `key:value` rows updated (`key:\tv` is now a mapping). Replace the "every line is lexed independently" subsection with the text-context rule: `a: Note\n  warning: do not touch` → `{"a": "Note\nwarning: do not touch"}` (was ERROR). |
| §8.1 | Unchanged example; it still raises. |
| §8.3 | Output line matches the code: `ERROR: DuplicateKeyError: Duplicate key 'key'` (Contract 03 makes the code produce it). |
| §8.4 | Last paragraph: a tab after `-`/`:` is separator whitespace (§7.5), not this error. |
| §8.5, §13.4 | Limits are recommendations; `DocumentLimitError` is the name for an implementation that enforces them; `syml` enforces none (FR-017). |
| §9.1 | Step 3: drop comment classification; blank lines are skipped by the builder, and paragraph breaks are recovered from line positions (§5.1). |
| §9.3 | KeyValue row unchanged in text (`level > keyvalue.level`), now true of the code. TextLeaf paragraph: add the text-context rule (a candidate at or past the threshold is accepted as text whatever it lexed as). Delete "`key: \t` has the one-character value `\t`" (R-11). |
| §10.2 | Add R-09's BOM sentence. State the `str(error)` form (FR-011) and that its rendered filename and line escape non-printable characters (`\xa0`, `\x1b`, `\t`, `\n`, lone surrogates) while `message` and `line_text` stay raw (Contract 03). |
| §11.1 | "an empty document or a document containing only blank lines". |
| §11.2.1 | Rewrite to Contract 04's eight items (item 2 including its later-line clause: more than 32 leading `- ` markers, a fixed count); B/C/D/G letters kept for references; add the inline-first spelling as a v1.x candidate (R-05). The opening sentence ("a conforming `dumps` has exactly one way to write each string … such that `loads(dumps(x)) == x`") is false under D21, because the L1 family has an inline-first spelling `dumps` does not use: say instead that `dumps` writes each string in one canonical layout, and name the three load-only families (Contract 04 L1–L3) as values `loads` can return that `dumps` refuses (red team outer iteration 7). The "MUST raise rather than emit text that would not read back" guarantee covers a value's text; say that structural depth is §13.4's cliff and `dumps` does not check it (a list nested past about 120 levels is written as one `- - …` line that `loads` cannot read; red team outer iteration 8, plan open question 9). |
| US3 narrative (spec.md, not §11.2.1) | **Applied in `spec.md` by red team outer iteration 3; the spec leaf only checks it still holds.** The closing sentence "the residual unrepresentable set is exactly the values that have no spelling at all" is false by R-05's own finding (the inline-first mapping family, `{"k": "a: 1\nb"}`, has a spelling but stays refused). Reword to something the code actually satisfies, e.g. "the residual unrepresentable set shrinks to the eight families FR-006 names, one of which (a structure-shaped first line at a mapping position) keeps a spelling `dumps` still declines to use." This is a spec-leaf obligation, not a code obligation: FR-006/`dumps` are unchanged by it. The rewording must also not claim that every value `loads` returns can be written: name all three load-only families (Contract 04 L1–L3: the inline-first mapping spelling; rule D's control characters that §4.6.1 reads verbatim; and a later line with more than 32 leading `- ` markers, red team outer iteration 7), matching §11.2.1's row above. Record the red team's verdict (plan open question 3) in spec.md's Clarifications. |
| FR-016, US4 scenario 4 (spec.md) | **Applied in `spec.md` by red team outer iteration 3.** Both said the comments item warns that files with `#` lines are "loud"/"change meaning". Reword so the obligation matches the behaviour: a `#`/`//` line that is the first line of a document or block makes that document or block one string, silently; a later one at a container's level raises. Record the correction in spec.md's Clarifications (red team pass 1, plan open question 7). |
| §11.2.3 | Keys: exactly `[a-z][a-z0-9_-]*`; everything else raises. Delete the quoted-key/`#` v1.2 note or reduce it to the quoted-key candidate. |
| §11.3 | Contract 05 wording: add `EncodingError`; `DocumentLimitError` reserved. |
| §12.1 | Remove the `# Application configuration` line. |
| §13.1–§13.3 | Remove comment and White_Space-in-key references; keep §13.3's LF-only line boundary. |
| §13.4 | Name the second recursion shape next to the nesting cliff: a line of many `- ` markers raises `RecursionError` from the per-line lex even inside a text value (§5.1), and `dumps` refuses to write a later line with more than 32 (§11.2.1), a fixed bound chosen well under the cliff because the cliff moves with the caller's stack depth. Figures from R-17 measurement 5, including the cliff at a shallow stack and with 500 frames already in use. Also state that `dumps` writes a nested list inline (`- - x`), so its output for nesting deeper than measurement 6's figure does not load, and that this depth is lower than the block-nesting cliff (red team outer iteration 8). |
| §14 | Rewrite the 1.0 row's comment, key, blank-line, D13, and tab clauses to the revised rules (keep it one row). |

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
| D23 | SYML has no comments; `#` and `//` are text everywhere. | Keep whole-line comments and document the continuation case (`syml-xreq.21` option a). | §4.3, M6's fix, B9's exception | Any `#`/`//` line changes meaning: text inside a value; `OutOfContextNodeError` at a container's level after its first entry; and, **silently**, a first line of the document or of a block makes that whole document or block one string (`# header\nk: v` → `"# header\nk: v"`; `a:\n  # s\n  b: 1` → `{"a": "# s\nb: 1"}`); and, **silently one level down**, a `#`/`//` after `key:` or `-` (YAML's trailing comment) is that key's or item's text value and takes in the block under it (`server: # prod\n  host: x` → `{"server": "# prod\nhost: x"}`, raised in 1.0; red team outer iteration 5). The ruling's "all loud" premise holds only for the middle case. |
| D24 | A tab is separator whitespace after `key:` and `-` (`ws = [ \t]+`); a marker followed only by spaces/tabs is bare; a tab in indentation still raises. A separator tab counts as one column for §6.2's sibling column. | Make a post-marker tab an error (v1.2 candidate 4). | D5 | `k:\tv` was `"k:\tv"`, is `{"k": "v"}`; `k: \tv` was `{"k": "\tv"}`, is `{"k": "v"}`. After `-\tk: v`, a sibling key goes at column 2; a line an editor shows aligned under `k` at a tab stop joins `v` silently. |
| D25 | Children are strictly deeper than their parent, list items included; the YAML indentless sequence is an error with a hint. §6.2's `- key:` sibling-column rule stands. | Keep the undocumented carve-out and add a KeyValue row to §9.3 (`syml-xreq.3` recommendation). | — (restores §4.2 rule 5 / §9.3 over code) | `k:\n- a` was `{"k": ["a"]}`, is `OutOfContextNodeError`. |

Annotate in place (the D18 precedent: a bold "Superseded by Dnn (2026-09-24)"
lead-in, text otherwise left): D5 → D24, D12 → D22, D13 → D21, D15 → D20,
D19 → D20. Annotate M6 and M20 ("closed by D23/D22"), M21 ("moot under D20"),
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
kept; D23 comments removed, stating **both** halves for any third-party
`.syml` file with `#` lines: a `#` line after a container's first entry now
raises, and a `#` header line at the top of the file or of a block silently
turns that file or block into one string, and a `#`/`//` after `key:` or `-`
(`server: # prod`) silently makes the block under it part of that key's
string. The item says how to check: search the file for every line whose
first non-space characters are `#` or `//`, and every `key:` or `-` followed
by separator whitespace and `#` or `//`. A hit of the first kind changes
meaning; a hit of the second kind changes meaning only when a deeper block
follows it (`k: # x` alone was already the string `"# x"` in 1.0), so the
item says to check what that key loads to. A
top-level `isinstance(loads(text), dict)` check is **not** the advice (red
team outer iteration 5): it passes for `server: # prod\n  host: x`, whose
damage is one level down. The "loud" wording of the ruling is not
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

## D. `README.md` (release leaf)

1. **"Coming from YAML"** section, in this order, each with the SYML spelling
   beside it (FR-015, US4 scenario 5):
   1. No comments: `# note` is text; keep notes in a value or outside the file.
      A `#` header line at the top of a file or block makes that whole file
      or block one string, with no error; so does a trailing comment after a
      key (`server: # prod` makes the block under it part of `server`'s
      string).
   2. No block-scalar indicators: `|` and `>` are literal; indent the lines
      under the key instead.
   3. No document markers: `---` and `...` are text (a document starting with
      one is a single string).
   4. No quoting: `"x"` keeps its quotation marks.
   5. `null`, `true`, `123`, `~`, `[a, b]`, `{a: 1}` are plain strings.
   6. Keys are `[a-z][a-z0-9_-]*`: `Name:`, `firstName:`, `URL:` are text, and
      a block of them (`env:\n  HOME: /h`) is one text value; so is a whole
      file whose first line is one (`Name: app\nport: 80` is a string), and
      so is a list item whose first key is one
      (`- containerPort: 80\n  protocol: TCP` is one string). A bad key
      after a good one raises with a hint.
   7. `- key:` sets a sibling column: `- server:\n  host: x` is two siblings;
      `- server:\n    host: x` nests (show both). Use a space after `-`:
      a tab there counts as one column.
   8. A blank line inside a value is a paragraph break.
2. A **`Source`** paragraph with Contract 05's three facts (FR-014).
3. Any README example that uses a comment line, a key outside
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
   Contract 04's eight items in plain words (no "leading space", "blank or
   `#`-initial or structure-shaped line inside a multi-line value", or
   "uppercase letter" wording), with the key rule stated as the pattern.

## E. Other text

- `CLAUDE.md` § Architecture: every line lexes as `indent (structure / data)`
  under `document = (line "\n")* line?`; the tree builder's text context
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

## Test obligations

1. `tests/test_spec_examples.py` passes over the edited spec with the new
   minimum count (SC-005, US4 scenario 1).
2. The grammar-identity test (Contract 01).
3. The §11.3-vs-exports test (Contract 05).
4. `tests/acceptance/test_us09_release_readiness.py`'s CHANGELOG assertions
   (built for 001) are updated for the rewritten items rather than deleted.
5. A US13 acceptance scenario reads the README section headings and asserts
   the eight items in order.
6. A unit test reads `README.md`, extracts the lead example's document and
   its printed result (the first two fenced `python` blocks), and asserts
   `loads(document) == ast.literal_eval(result)`, so the README's first
   example cannot again drift from the parser. It replaces the two
   hand-copied `test_parsers.py` README tests or sits beside them (red team
   outer iteration 4).
