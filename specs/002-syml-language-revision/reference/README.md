# Reference material for the language revision

Copied from the 2026-09-24 break-test session's scratchpad (lanes 1 and 4 of
the campaign recorded in beads epic `syml-xreq`) so the evidence survives the
scratchpad. Nothing here is a test; planning decides what becomes a fixture.

## `lane-4-documents/`

Thirty-four hand-written documents with a companion `*.expected.py` each.
Every companion defines:

- `SOURCE` — the document text (identical to the `.syml` file).
- `SPEC` — what SYML 1.0 *as written before this revision* produces, either a
  value or `('error', '<ErrorClass>')`.
- `AUTHOR` — what the document's human author naively expected, written
  **before David's rulings**. It is the usability lens, not the ruling.

Read `AUTHOR` as evidence of the surprise, not as the expected value. The
expected value after this revision is derived from the rulings (FR-001 to
FR-017 in `../spec.md`). Known divergences between `AUTHOR` and the rulings:

- `doc01b_scene_taxi` opens with `Given:`; under the key rule that line is
  text, and under the text-context rule a root document whose first line is
  text is text throughout. The author would lowercase the key.
- `doc08e_yaml_list_in_map_same_indent`: strict indentation stands, so it
  remains an error (now with a hint for the same-column list).
- `doc05c_three_space_sibling`, `doc05d_item_one_deeper`: **not errors after
  this revision** (corrected during planning, research.md R-06). Each
  over-indented line follows an inline value, so the text-context rule makes
  it a continuation: `doc05c` loads as
  `{"parent": {"child1": "a", "child2": "b\nchild3: c"}}` and `doc05d` as
  `["milk", "eggs\n- bread"]`.
- `doc06_shopping` / `doc06b_shopping_clean`: `Eggs: 12` is text (key rule);
  `- bread` followed by a deeper `- rye` is a continuation of the text
  `bread`, not a nested list (text-context rule).
- `doc07_a`, `_b`, `_e`, `_f`: `First Name`, `firstName`, `URL`, `x-API-key`
  are not keys; at root, the first-line rule makes the document text or the
  second line a continuation, depending on position.
- `doc08_yaml_user`, `doc08b_block_scalar`, `doc08c_doc_markers`: YAML syntax
  is literal text; `# trailing` is not stripped (no comments); `|` and `>`
  are literal; `---` and `...` are text lines and, at root, make the document
  a root scalar.
- `doc09c_only_comments`, `doc09g_comment_no_nl`: with comments removed,
  these load as the text of their lines, not the empty string.

## `lane-1-roundtrip-probe.py`

The Hypothesis harness from lane 1 (properties P1–P7). Run from the repo
root with `uv run --with hypothesis python <path> [prop ...]`; `FILTER_KNOWN=0`
disables the exclusion of the families that were known-broken on `27a3e9a`.
The success criterion for this feature is that it passes with
`FILTER_KNOWN=0` once its strategies are updated for the revised language
(key pattern, no comments, paragraph breaks, text context).
