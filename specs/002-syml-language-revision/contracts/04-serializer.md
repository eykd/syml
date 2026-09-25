# Contract 04 — `dumps` Writes Everything the Parser Reads

**Requirements**: FR-002, FR-006, FR-014, FR-017 (`dumps('')`) | **Decisions**: D20, D21, D22, D23, D24 (serializer halves) | **Findings closed**: `syml-xreq.6`, `.12`, `.15` / `.16` / `.2` / `.1` (serializer halves), `.23` (code half) | **Research**: R-05, R-14, R-18

## Surface

```python
def dumps(data: SymlInput) -> str: ...
def dump(data: SymlInput, file_obj: IO[str]) -> None: ...
def key_is_representable(k: str) -> bool: ...   # re.fullmatch(r'[a-z][a-z0-9_-]*', k) is not None
```

`key_is_representable` changes in the **grammar leaf**, not the serializer
leaves: today it calls `parsers.key_has_uppercase`, which Contract 01 removes
there, and it matches with the grammar's `key` rule, so the rewrite to the
regex has to land in the same commit to keep mypy and `dumps` working (red
team outer iteration 4, plan § Existing tests that invert).

Signatures are unchanged. `SymlInput` is unchanged; a `Source` is accepted at
runtime wherever a `str` key or scalar is (FR-014). The static type does not
widen: `as_source()` already returns `Any`, so `dumps(parse(t).as_source())`
type-checks today.

## Layout (unchanged except where noted)

- Single-line value at a mapping or list position: inline, after exactly one
  space (`key: v`, `- v`).
- Multi-line value: block form; `key:` / `-` alone, each line two spaces past
  the marker. **New**: an empty line of the value (a paragraph break) is
  written as an empty physical line with no indentation.
- Root scalar: block form at column 0; **new**: leading spaces on its first
  line are written as-is (FR-005).
- `dumps('')` → `''` (**changed**, was `'\n'`). Any other output ends in
  exactly one `\n`. The extra-BOM rule for output beginning with U+FEFF is
  unchanged.
- Keys in insertion order; rule G (one space after `-` before an inline key)
  unchanged.

## Unrepresentable set (§11.2.1 as revised; R-05)

`UnrepresentableValueError` is raised for, and only for:

| # | Condition | Positions |
| --- | --- | --- |
| 1 | a control character other than LF and TAB (includes `\r`) | all |
| 2 | first line is structure-shaped: `grammar['structure']` fully matches `line.lstrip(' ')`, with **no** §9.0 pre-processing (a `RecursionError` counts as structure). **Also (red team outer iterations 3 and 7):** any later line of a multi-line value whose leading list-marker chain holds more than `MAX_LATER_LINE_MARKERS = 32` markers: after the line's leading spaces, the match of `(?:-[ \t]+)*-?` contains more than 32 `-` characters (a long `- - - …` chain: D21 makes it text, but the per-line lex still recurses once per marker). The check is a count, never a parse: the lex cliff moves with the caller's stack (about 122 markers at a shallow stack, about 60 with 500 frames in use, on the planning spike), so a parse probe run inside `dumps` would make `dumps`' answer depend on where it is called and could write a line that a deeper `loads` cannot read. 32 markers costs `loads` roughly a quarter of the default recursion limit (R-17 measures it) | first line: list (single- or multi-line); mapping (multi-line only); root. Later line: all |
| 3 | first line begins with a space | mapping, list |
| 4 | any line's leading run of spaces and tabs contains a tab | all |
| 5 | any line is non-empty and consists only of spaces and tabs | all |
| 6 | the value has more than one line and its first or last line is empty | all |
| 7 | a mapping key that does not match `[a-z][a-z0-9_-]*` (incl. `""`) | — |
| 8 | an empty list or mapping (§11.2.2, unchanged) | — |
| 9 | any line that begins with `#` or `//` (it would be written at column 0 and read back as a comment, FR-007; principal ruling 2026-09-24, R-18). The refusal message keeps 1.0's reason text, `a line begins with a comment marker` | root |

**Item 9 is root-only, and nothing else can put a marker at column 0.** A
root scalar is written in block form at column 0 and its baseline is column
0, so indentation cannot protect a `#` line: it would become part of the
value. Every other line `dumps` writes starts with a key (`[a-z]`), a `-`,
or at least two spaces, or is an empty paragraph-break line. A value that
starts with a BOM and then `#` is still written: the output's extra BOM
(unchanged rule) makes `loads` strip one and keep `\ufeff# x` as content.

`TypeError` for anything that is not `str`, `Source`, `list`, or `dict`, and for
a non-`str`, non-`Source` key (unchanged apart from accepting `Source`).

## Behaviour

| # | Input | `dumps` output | round trip |
| --- | --- | --- | --- |
| US3-1 | `{"k": "Para one.\n\nPara two."}` | `k:\n  Para one.\n\n  Para two.\n` | yes |
| US3-2 | `{"k": "some prose\n- used as a dash\nkey: v"}` | `k:\n  some prose\n  - used as a dash\n  key: v\n` | yes |
| US3-3 | `"  hello\nworld"` | `  hello\nworld\n` | yes |
| US3-4 | `["- x"]`, `["a: 1"]`, `["\n"]` | `UnrepresentableValueError` (items 2, 2, 6) | — |
| US3-5 | `["\ufeff- x"]` / `{"k": "a\n\ufeff- x"}` | `- \ufeff- x\n` / `k:\n  a\n  \ufeff- x\n` | yes |
| US3-6 | `["\xa0x"]`, `"\xa0x"`, `{"k": "a\n\xa0b"}` | `- \xa0x\n`, `\xa0x\n`, `k:\n  a\n  \xa0b\n` | yes |
| US3-7 | `{"Name": …}`, `{"1st": …}`, `{"e.mail": …}`, `{"名前": …}`, `{"": …}` | `UnrepresentableValueError` (item 7) | — |
| US3-7 | `{"first-name": "x"}`, `{"first_name": "x"}`, `{"choice1": "x"}` | `first-name: x\n` etc. | yes |
| US3-8 | `parse("k: v").as_source()` | `k: v\n` | yes |
| US3-9 | `""` | `""` | yes (`loads("") == ""`) |
| US3-10 | `{"k": "\r"}` / `{"k": "a\tb"}` | `UnrepresentableValueError` / `k: a\tb\n` | — / yes |
| R-05 | `{"k": "a\n \nb"}`, `{"k": "a\n  \tb"}`, `{"k": "\ta"}`, `"x\n"` | `UnrepresentableValueError` (items 5, 4, 4, 6) | — |
| R-05 | `{"k": "# x"}`, `["# x"]`, `{"k": "a\n# b"}`, `["a\n# b"]` | `k: # x\n`, `- # x\n`, `k:\n  a\n  # b\n`, `-\n  a\n  # b\n` | yes |
| R-18 | `"# x"`, `"// x"`, `"# x\n// y"`, `"a\n# b"`, `"a\n// b"` | `UnrepresentableValueError` (item 9; `"# x\n// y"` was written in the pre-ruling plan) | — |
| R-18 | `"  # x"`, `"a\n  # b"`, `"\ufeff# x"`, `"/x"`, `"a\n/b"` | `  # x\n`, `a\n  # b\n`, `\ufeff\ufeff# x\n`, `/x\n`, `a\n/b\n` | yes |
| R-05 | `{"k": "a: 1\nb"}` | `UnrepresentableValueError` (item 2; see R-05 "one family refused despite having a spelling") | — |
| recursion | `{"k": "a\n" + "- " * 1000 + "x"}`, `["a\n" + "- " * 1000 + "x"]`, `"a\n" + "- " * 1000 + "x"` | `UnrepresentableValueError` (item 2, later line); `loads` of the same text written by hand raises `RecursionError` (documented, not fixed: plan § Edge Cases, "A `- ` chain is text but still recurses") | — |
| recursion | `{"k": "a\n" + "- " * 32 + "x"}` / `{"k": "a\n" + "- " * 33 + "x"}` | written and round-trips / `UnrepresentableValueError` (item 2, later line): the bound is exact and does not move with the stack | yes / — |
| recursion | `{"k": "a\n" + "-\t" * 33 + "x"}`, `{"k": "a\n  " + "- " * 32 + "-"}` (33 markers, the last bare) | `UnrepresentableValueError` (item 2; tabs separate markers too, and a final bare `-` counts) | — |
| recursion | `{"k": "a\nk: " + "- " * 100 + "x"}`, `{"k": "a\n" + "- " * 20 + "x"}` | written; round-trips (a chain after `k: ` is inline `data` and does not recurse; a short chain is an ordinary later line) | yes |
| load-only | `dumps(loads("k:\n  a\n  " + "- " * 40 + "x"))` | `UnrepresentableValueError` (item 2, later line): `loads` reads a 40-marker chain at a shallow stack, `dumps` refuses it at every stack (family L3) | — |
| load-only | `dumps(loads("k: note: the door\n  is locked"))`, `dumps(loads("notes: - milk\n  - eggs"))` | `UnrepresentableValueError` (item 2): values `loads` returns that `dumps` refuses (red team pass 1; kept, plan open question 3) | — |
| load-only | `dumps(loads("\x0bx"))`, `dumps(loads("k: a\x1cb"))` | `UnrepresentableValueError` (item 1): §4.6.1 reads controls verbatim, rule D still refuses them (US3 scenario 10) | — |

### Load-only families

Exactly three families of values can come out of `loads` and be refused by
`dumps`: (L1) a multi-line value at a mapping position whose first line is
structure-shaped (item 2 at a mapping position), (L2) a value containing a
character rule D refuses (item 1), and (L3) a multi-line value with a later
line whose leading marker chain holds more than 32 markers but that the
caller's stack still let `loads` read (item 2, later-line clause; red team
outer iteration 7). Every other value `loads` returns is written by `dumps`
and round-trips. P8 below pins this.

Item 9 adds **no** load-only family (R-18): `loads` never returns a root
scalar with a line that begins with `#` or `//`, because such a line at
column 0 is a comment and never becomes text, and an indented one keeps its
leading spaces in the value.

**Not checked: structural nesting** (red team outer iteration 8, plan open
question 9; the principal ruled "document only" on 2026-09-24). Item 2's count looks at a value's text lines only. A nested list
is written inline (`[["x"]]` → `- - x`), so `dumps` of a list nested 130 deep
writes one line that `loads` cannot read (the lex cliff is about 121 levels
at a shallow stack, 58 with 500 frames in use; identical on `master`). That
is the §13.4 nesting cliff, documented and not enforced (Scope Boundaries);
§11.2.1's guarantee is scoped to a value's text (Contract 06 §A). The
property strategies must keep nesting well under that depth, and no test
pins the deep case either way: the depth is documented in §13.4, not
enforced or tested.

## Test obligations

1. Every row above.
2. **SC-002 property** (`tests/test_roundtrip_property.py`, R-14): for every
   generated value `x`, either `dumps(x)` raises `UnrepresentableValueError`
   or `TypeError`, or `loads(dumps(x)) == x` and `dumps(loads(dumps(x))) == dumps(x)`;
   no excluded input family. Plus P3, P4, P5, P7 from the lane-1 probe.
   **P8 (load first, red team pass 1):** for every generated *document* `t`
   (the P3 strategy: lines built from indentation, markers, keys, `#`, `//`
   at column 0 and indented, NBSP, BOM, tabs, controls, and text) for which `loads(t)` returns `x`,
   either `loads(dumps(x)) == x`, or `dumps(x)` raises
   `UnrepresentableValueError`, `x` contains a value in family L1, L2 or L3
   (checked by a predicate written against the definitions above, not by
   calling `dumps`; the L1 predicate uses `_lexes_as_structure`, so a long
   `- ` chain as a mapping value's first line is classified as structure
   rather than raising `RecursionError` in the test), **and** `x'`, the value
   with every L1/L2/L3 scalar replaced by `"x"`, round-trips
   (`loads(dumps(x')) == x'`). The last clause is what makes P8 an oracle
   (red team outer iteration 7): `dumps` stops at the first value it refuses,
   so "`x` contains an L1 value" alone would pass a document that also holds
   a wrongly refused value elsewhere, and the one family P8 exists to catch
   (a third, unplanned load-only family) would hide behind any L1 value in
   the same document. A fourth load-only family fails P8. P8 also asserts
   that no line of `dumps(x)` begins with `#` or `//` (R-18).
   **P9 (comments are as if absent, R-18):** for every generated document
   `t`, with `u` the text after §9.0's index-0 BOM strip and `u'` that text
   with every line that begins with `#` or `//` deleted, `loads(t)` equals
   `loads("\ufeff" + u')` (the prefixed BOM keeps a BOM that `u'` starts
   with from being stripped a second time), and when one raises the other
   raises the same class.
   **Hypothesis settings** (plan § Performance Considerations): a `gate`
   profile (`deadline=None`, `derandomize=True`, a few hundred examples per
   property) registered in `tests/conftest.py` and loaded by default, a
   `fuzz` profile selected by `HYPOTHESIS_PROFILE=fuzz`, a `just fuzz`
   recipe, and `.hypothesis/` in `.gitignore`, all in the leaf that adds the
   property file. No `src/` branch may be covered only by generated inputs.
3. `key_is_representable` agrees with `re.fullmatch(r'[a-z][a-z0-9_-]*', k)`
   (P7) and with the grammar: a key it accepts round-trips as a key.
4. `_lexes_as_structure` does not strip a BOM or NBSP and treats a
   `RecursionError` as structure (only the first-line check parses; a first
   line refused at one stack depth is refused at every depth, because both a
   successful structure match and a `RecursionError` refuse it). The
   later-line check (item 2) is the marker count, with no parse and no
   `RecursionError` handling: the 32/33 boundary rows above are exact, and a
   test calls `dumps` on the 33-marker row from inside a helper that has
   already used 500 frames and from a shallow stack and gets the same
   result.
5. The existing `tests/serialization_corpus.py` rows that pinned D12, D13,
   indented comments, and D19 are rewritten to the rows above (plan §
   Inverted tests). `block_line_begins_with_comment_marker`
   (`{"k": "a\n# c"}`) moves from refusal to round trip;
   `comment_marker_root_scalar` (`"# c"`) stays a refusal, now by item 9.
   By name, besides those the plan lists: `lowercase_roman_numeral_key`
   (`{"\u217b": "x"}`) and `leading_feff_first_key` (`{"\ufeffk": "v"}`) move
   from round-trip to item-7 refusals; `colon_escape_list_item`
   (`["a\\: b"]`, now a text item) moves from refusal to round trip, and its
   `TestDumpsStructureShapedStringsArePositionDependent` case (which expects
   the list item refused beside the mapping value) is dropped (these three in
   the grammar leaf);
   `leading_space_root_scalar` (`"  hello"`) and
   `block_line_lexes_as_structure` (`{"k": "a\n  - b"}`) move from refusal to
   round trip (serializer leaves). The plan's spike-run command is the
   inventory; this list is what it found at `21eae88`.
