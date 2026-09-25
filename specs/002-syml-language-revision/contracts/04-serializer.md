# Contract 04 — `dumps` Writes Everything the Parser Reads

**Requirements**: FR-002, FR-006, FR-014, FR-017 (`dumps('')`) | **Decisions**: D20, D21, D22, D23, D24 (serializer halves) | **Findings closed**: `syml-xreq.6`, `.12`, `.15` / `.16` / `.2` / `.1` (serializer halves), `.23` (code half) | **Research**: R-05, R-14

## Surface

```python
def dumps(data: SymlInput) -> str: ...
def dump(data: SymlInput, file_obj: IO[str]) -> None: ...
def key_is_representable(k: str) -> bool: ...   # re.fullmatch(r'[a-z][a-z0-9_-]*', k) is not None
```

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
| 2 | first line is structure-shaped: `grammar['structure']` fully matches `line.lstrip(' ')`, with **no** §9.0 pre-processing | list (single- or multi-line); mapping (multi-line only); root |
| 3 | first line begins with a space | mapping, list |
| 4 | any line's leading run of spaces and tabs contains a tab | all |
| 5 | any line is non-empty and consists only of spaces and tabs | all |
| 6 | the value has more than one line and its first or last line is empty | all |
| 7 | a mapping key that does not match `[a-z][a-z0-9_-]*` (incl. `""`) | — |
| 8 | an empty list or mapping (§11.2.2, unchanged) | — |

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
| R-05 | `{"k": "# x"}`, `"# x\n// y"`, `{"k": "a\n# b"}` | `k: # x\n`, `# x\n// y\n`, `k:\n  a\n  # b\n` | yes |
| R-05 | `{"k": "a: 1\nb"}` | `UnrepresentableValueError` (item 2; see R-05 "one family refused despite having a spelling") | — |
| load-only | `dumps(loads("k: note: the door\n  is locked"))`, `dumps(loads("notes: - milk\n  - eggs"))` | `UnrepresentableValueError` (item 2): values `loads` returns that `dumps` refuses (red team pass 1; kept, plan open question 3) | — |
| load-only | `dumps(loads("\x0bx"))`, `dumps(loads("k: a\x1cb"))` | `UnrepresentableValueError` (item 1): §4.6.1 reads controls verbatim, rule D still refuses them (US3 scenario 10) | — |

### Load-only families

Exactly two families of values can come out of `loads` and be refused by
`dumps`: (L1) a multi-line value at a mapping position whose first line is
structure-shaped (item 2 at a mapping position), and (L2) a value containing a
character rule D refuses (item 1). Every other value `loads` returns is
written by `dumps` and round-trips. P8 below pins this.

## Test obligations

1. Every row above.
2. **SC-002 property** (`tests/test_roundtrip_property.py`, R-14): for every
   generated value `x`, either `dumps(x)` raises `UnrepresentableValueError`
   or `TypeError`, or `loads(dumps(x)) == x` and `dumps(loads(dumps(x))) == dumps(x)`;
   no excluded input family. Plus P3, P4, P5, P7 from the lane-1 probe.
   **P8 (load first, red team pass 1):** for every generated *document* `t`
   (the P3 strategy: lines built from indentation, markers, keys, `#`, `//`,
   NBSP, BOM, tabs, controls, and text) for which `loads(t)` returns `x`,
   either `loads(dumps(x)) == x`, or `dumps(x)` raises
   `UnrepresentableValueError` and `x` contains a value in family L1 or L2
   (checked by a predicate written against the definitions above, not by
   calling `dumps`). A third load-only family fails P8.
   **Hypothesis settings** (plan § Performance Considerations): a `gate`
   profile (`deadline=None`, `derandomize=True`, a few hundred examples per
   property) registered in `tests/conftest.py` and loaded by default, a
   `fuzz` profile selected by `HYPOTHESIS_PROFILE=fuzz`, a `just fuzz`
   recipe, and `.hypothesis/` in `.gitignore`, all in the leaf that adds the
   property file. No `src/` branch may be covered only by generated inputs.
3. `key_is_representable` agrees with `re.fullmatch(r'[a-z][a-z0-9_-]*', k)`
   (P7) and with the grammar: a key it accepts round-trips as a key.
4. `_lexes_as_structure` does not strip a BOM or NBSP and treats a
   `RecursionError` as structure.
5. The existing `tests/serialization_corpus.py` rows that pinned D12, D13,
   comments, and D19 are rewritten to the rows above (plan § Inverted tests).
