# Feature Specification: SYML Language Revision — Values Are Just Text

**Feature Branch**: `002-syml-language-revision`
**Created**: 2026-09-24
**Status**: Draft
**Input**: User description: "syml language revision: values are just text"
**Brainstorm**: `specs/brainstorms/2026-09-24-syml-language-revision-requirements.md` (R1–R17; every requirement cites its ruling in beads epic `syml-xreq`, whose description is the break-test campaign report)
**Break-test findings**: beads epic `syml-xreq`, children `.1`–`.24` (label `break-test`; the twelve ruled ones also carry `ruled`)
**Reference material**: `specs/002-syml-language-revision/reference/` (the lane-4 human-usability documents and the lane-1 round-trip probe, preserved from the campaign scratchpad; see its README for how to read them)
**Beads Epic**: `syml-s9p9`
**Beads Phase Tasks**:

- plan: `syml-s9p9.1`
- red-team: `syml-s9p9.2`
- tasks: `syml-s9p9.3`
- analyze: `syml-s9p9.4`
- implement: `syml-s9p9.5`
- harden: `syml-s9p9.6`

## Clarifications

### Session 2026-09-24

- Q: Found brainstorm doc at `specs/brainstorms/2026-09-24-syml-language-revision-requirements.md`. Use it as input for this specification? → A: Yes (answered in advance by the handoff plan that launched this phase). R1–R17 are the authoritative requirement list; the `syml-xreq` issues supply the repros for the acceptance scenarios.
- Q: Is tagging and pushing `1.0.0` in scope, and is uploading to PyPI? → A: Tagging and pushing the (still unpushed) `1.0.0` tag is in scope: the handoff plan's end state requires it. Building and uploading a distribution to PyPI stays a separate manual step after the tag, as spec 001 decided.
- Q: Does the `syml-xreq` break-test epic get merged into this feature's epic? → A: No. Its 24 children stay where they are and are linked to this feature's epic with `related` dependencies so nothing is duplicated; each implementation task closes the child it pins (see Assumptions for the ready-queue hazard this creates).

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Prose, dialogue, and headers are text, all the time (Priority: P1)

An interactive-fiction author writes scene text under a list item: a paragraph, a
blank line, a second paragraph, a line that starts with a dash, a line that starts
with `Note:` or `//server/share`. Today the parser reinterprets lines inside the
value: the blank line vanishes, the dash line becomes a nested list (or an error),
the `//` line is deleted as a comment, and a capitalized header blames the line
after it. After this feature, structure is decided at the first line of a block and
at inline positions only; once a value is text, every following line at or past its
baseline is that value's text, a blank line between two such lines is a paragraph
break, `#` and `//` have no meaning, and a key is exactly `[a-z][a-z0-9_-]*`.

**Why this priority**: This is the organizing principle of the revision and the
source of every silent surprise in the lane-4 documents. It is also the only story
that changes the language's grammar; the other three stories are consequences,
tooling, and release text.

**Independent Test**: Load the lane-4 interactive-fiction and prose documents
(`doc01_scene_cellar`, `doc01b_scene_taxi` with its header lowercased,
`doc03_prose`, `doc03b_prose_root`) and the repro inputs from `syml-xreq.15`,
`.16`, `.17`, `.21`, `.22`, `.2`; assert the values the rulings give, with no
serializer or error-message change required.

**Acceptance Scenarios**:

1. **Given** `k:\n  Para one.\n\n  Para two.`, **When** loaded, **Then** the result is `{"k": "Para one.\n\nPara two."}` (the blank line between two continuation lines is kept).
2. **Given** `Para one.\n\nPara two.`, **When** loaded, **Then** the result is `"Para one.\n\nPara two."`.
3. **Given** `k:\n  some prose\n  - used as a dash\n  more`, **When** loaded, **Then** the result is `{"k": "some prose\n- used as a dash\nmore"}` (a continuation line shaped like a list item is text).
4. **Given** `- Share is\n  //server/share` and `- tag line\n  #winning`, **When** loaded, **Then** the results are `["Share is\n//server/share"]` and `["tag line\n#winning"]` (no comments).
5. **Given** `port: 8080 # default`, **When** loaded, **Then** the result is `{"port": "8080 # default"}` (unchanged; `#` is text inline too).
6. **Given** `- [ask: why?]`, `- "listen: I know."`, `- 3: 1 odds`, and `"so: you came back."`, **When** loaded, **Then** every one is text: `["[ask: why?]"]`, `["\"listen: I know.\""]`, `["3: 1 odds"]`, and the root scalar `"\"so: you came back.\""`.
7. **Given** `env:\n  HOME: /h\n  PATH: /p`, **When** loaded, **Then** the result is `{"env": "HOME: /h\nPATH: /p"}` (uppercase would-be keys are text; the README documents this).
8. **Given** `name: a\nfirstName: b\nage: 3`, **When** loaded, **Then** `OutOfContextNodeError` is raised at line 2 and its message carries the key-pattern hint (see User Story 2).
9. **Given** `Given:\n  a: 1`, **When** loaded, **Then** the result is the root scalar `"Given:\n  a: 1"`: the first line is text, so the document is text throughout, and the two spaces past the column-0 baseline are kept.
10. **Given** `  hello`, `  hello\nworld`, and `  hello\n    world`, **When** loaded, **Then** the results are `"  hello"`, `"  hello\nworld"`, and `"  hello\n    world"` (a root scalar keeps its leading indentation; the root baseline is column 0).
11. **Given** `k:\n  a\n\n\n  b\n\n`, **When** loaded, **Then** the result is `{"k": "a\n\n\nb"}`: blank lines between continuation lines are kept one for one; blank lines after the last continuation are inert, so a value never ends with a blank line.
12. **Given** `k:\n\n  a`, **When** loaded, **Then** the result is `{"k": "a"}` (a blank line before the first continuation line is inert).
13. **Given** `k:\n  a\n\nb: 2`, **When** loaded, **Then** the result is `{"k": "a", "b": "2"}` (a blank line between a value and the next key stays inert).
14. **Given** `# one\n// two\n  # three`, **When** loaded, **Then** the result is `"# one\n// two\n  # three"` (a document of former comment lines is a root scalar), and `# c` with no trailing newline is `"# c"`.
15. **Given** `a:\n  b: 1\n  # note`, **When** loaded, **Then** `OutOfContextNodeError` is raised (a `#` line at a mapping's level is text at a container's level, which §6.4 already forbids).
16. **Given** `k: first\n  - second\n  key: third`, **When** loaded, **Then** the result is `{"k": "first\n- second\nkey: third"}` (an inline value followed by deeper lines of any shape stays one text value).
17. **Given** `k:\n  - a\n  - b`, **When** loaded, **Then** the result is `{"k": ["a", "b"]}` (the first line of a block still decides structure), and **Given** `k:\n  x: 1\n  y: 2`, the result is `{"k": {"x": "1", "y": "2"}}`.
18. **Given** `k: a\n    b\n  c`, **When** loaded, **Then** `OutOfContextNodeError` is raised: `b` fixes the baseline at column 4, `c` sits below it, ends the value, and finds no context when re-offered (unchanged from 1.0).

---

### User Story 2 - Structure is strict, whitespace is honest, and errors say why (Priority: P1)

A configuration author indents a list at the same column as its key (a YAML habit),
puts a tab after a colon, or pastes a line that begins with a non-breaking space.
Today the first is silently accepted, the second silently turns the whole line into
text, and the third loses the character. After this feature, children are strictly
deeper than their parent, a tab after a marker is ordinary separator whitespace,
only the ASCII space is indentation, and a context error names the file, line,
column, the columns that were open, and (when it applies) a one-line hint.

**Why this priority**: These are the rulings that restore the spec over the code
(`.1`, `.2`, `.3`) plus the error-message work (`.17`, `.18`, `.19`) that keeps the
strictness from being hostile. The P1 defect in the campaign (`.1`) lives here.

**Independent Test**: Load the repro inputs from `syml-xreq.1`, `.3`, `.4`, `.5`,
`.18`, `.19`, `.20` and assert the ruled value or the ruled error text; no
serializer or documentation change is needed.

**Acceptance Scenarios**:

1. **Given** `k:\n- a\n- b`, **When** loaded, **Then** `OutOfContextNodeError` is raised and the message includes a hint that the list item sits at its key's column and must be indented past the key.
2. **Given** `a:\n- x\n- y\nb: z` and `- key:\n  - x`, **When** loaded, **Then** both raise `OutOfContextNodeError` (a child, list items included, must be deeper than its key).
3. **Given** `- server:\n  host: x`, **When** loaded, **Then** the result is `[{"server": "", "host": "x"}]` (the inline key sets the sibling column; §6.2 stands, and the README shows both layouts side by side).
4. **Given** `k:\tv`, `a:\t\n  b: 1`, and `- a\n-\tx`, **When** loaded, **Then** the results are `{"k": "v"}`, `{"a": {"b": "1"}}`, and `["a", "x"]` (a tab after a marker is separator whitespace; a marker followed only by spaces or tabs is a bare marker).
5. **Given** `a:\n\tb`, **When** loaded, **Then** `TabIndentationError` is still raised (a tab in leading indentation is unchanged).
6. **Given** `\xa0k: v`, **When** loaded, **Then** the result is the root scalar `"\xa0k: v"` (a non-breaking space is content, and a line that starts with content is not a key line).
7. **Given** `k:\n  a\n\xa0\n  b`, **When** loaded, **Then** `OutOfContextNodeError` is raised: the NBSP-only line is a text line at column 0, below the baseline, and it finds no context when re-offered.
8. **Given** `\x0bx`, `\x0c`, and `\u2028- x`, **When** loaded, **Then** the results are `"\x0bx"`, `"\x0c"`, and `"\u2028- x"` (vertical tab, form feed, and the line separator pass through verbatim per §4.6.1; none of them is indentation or a line break).
9. **Given** `k:\n  a: 1\n   b: 2`, **When** loaded, **Then** `str(error)` is `3:3: <message>` followed on the next line by `   b: 2`, and the message states that line 3 is at column 3 while the open blocks are at columns 0 and 2.
10. **Given** the same document loaded with `filename="f.syml"`, **When** the error is printed, **Then** `str(error)` begins `f.syml:3:3: ` and `error.message` begins `f.syml: `.
11. **Given** `a: 1\n  - x` and `a:\n\tb` loaded with `filename="f.syml"`, **When** they raise, **Then** both `.message` values begin with `f.syml: ` (every `ParseError` subclass carries the prefix).
12. **Given** `a: 1\r\n\tb: 2` and `\ufeff\tk: v`, **When** they raise `TabIndentationError`, **Then** `.position` points at the tab in the caller's original text: index 6, line 2, column 0 for the first (today it reports index 5, the line feed); index 1, line 1, column 1 for the second (today it reports index 0, the BOM).
13. **Given** `\ufeffa: b\r\n\tc: d`, **When** it raises, **Then** `.position` is index 7, line 2, column 0 (BOM and CRLF both accounted for).
14. **Given** `key: v\n\xa0\tx`, **When** loaded, **Then** no `TabIndentationError` is raised for the tab (the NBSP-led line is content at column 0, not indentation); the line is re-offered after the closed inline pair and raises `OutOfContextNodeError` instead.

---

### User Story 3 - The serializer writes everything the parser reads (Priority: P2)

A tool round-trips SYML through Python: it loads a document, edits a value, and
writes it back. Today `dumps` refuses paragraph breaks, later lines that look like
structure, indented root scalars, BOM-led lines that do round-trip, and the output
of `as_source()`, and it writes `""` as a newline. After this feature every value the
revised language can express is written, `dumps` reads `Source` keys and scalars as
their text, and the residual unrepresentable set is exactly the values that have no
spelling at all.

**Why this priority**: Round-trip fidelity is the property the campaign fuzzed
(lane 1); it depends on User Story 1's language changes landing first.

**Independent Test**: Run the round-trip property from
`reference/lane-1-roundtrip-probe.py` with no excluded input family, plus the
repro inputs from `syml-xreq.6`, `.12`, `.16` (the `dumps` half), `.23`.

**Acceptance Scenarios**:

1. **Given** `{"k": "Para one.\n\nPara two."}`, **When** dumped and loaded again, **Then** the value round-trips (paragraph breaks are written in block form as a blank line).
2. **Given** `{"k": "some prose\n- used as a dash\nkey: v"}`, **When** dumped and loaded again, **Then** the value round-trips (later lines of a multi-line value are unrestricted).
3. **Given** `"  hello\nworld"`, **When** dumped, **Then** the output is `  hello\nworld\n` and it loads back to the same string (an indented root scalar is written in block form at column 0).
4. **Given** `["- x"]`, `["a: 1"]`, and `["\n"]`, **When** dumped, **Then** `UnrepresentableValueError` is raised: a value whose first line lexes as structure at a list position, and a value that begins or ends with a blank line, have no spelling.
5. **Given** `["\ufeff- x"]` and `{"k": "a\n\ufeff- x"}`, **When** dumped and loaded again, **Then** both round-trip (a line that only looks like structure after BOM stripping is content).
6. **Given** `["\xa0x"]`, `"\xa0x"`, and `{"k": "a\n\xa0b"}`, **When** dumped and loaded again, **Then** each round-trips unchanged (a leading non-breaking space is content everywhere).
7. **Given** `{"Name": "x"}`, `{"1st": "x"}`, `{"e.mail": "x"}`, `{"名前": "x"}`, and `{"": "x"}`, **When** dumped, **Then** `UnrepresentableValueError` is raised; `{"first-name": "x"}`, `{"first_name": "x"}`, and `{"choice1": "x"}` are written.
8. **Given** the value returned by `parse("k: v").as_source()`, **When** dumped, **Then** the output is `k: v\n` (a `Source` key or scalar is written as its text).
9. **Given** the empty string, **When** dumped, **Then** the output is the empty document `""`, which loads back to `""`.
10. **Given** `{"k": "\r"}` or `{"k": "a\tb"}`, **When** dumped, **Then** the first raises `UnrepresentableValueError` and the second is written literally (control-character rules are unchanged; a tab inside a value is fine).

---

### User Story 4 - The documents describe exactly what ships, and 1.0.0 is tagged (Priority: P2)

A developer coming from YAML reads the README, then the specification, then the
changelog, and can predict every difference before hitting it. Today the changelog
claims internals and limits that do not exist, the printed grammar is not the one
the code runs, one error example shows a message the code never produces, and the
new language rules are recorded nowhere. After this feature the specification, the
review document's decision table, the changelog, and the README agree with the
code, and the `1.0.0` tag is pushed.

**Why this priority**: The rulings are only real once the spec says them, and the
plan orders spec revision before code so tests can be written from the spec. The
tag is the feature's end state.

**Independent Test**: Extract every `**Output:**` and `**ERROR:**` example from the
specification and run it; diff the printed §4.1 grammar against the grammar the
code declares; read the README section and the changelog items against the ruled
behavior; confirm the tag on the remote.

**Acceptance Scenarios**:

1. **Given** the revised `SYML-SPECIFICATION.md`, **When** every fenced `syml` block that states an Output or an ERROR is run, **Then** each produces exactly that output or raises exactly that error (54 today; the count follows the edited text).
2. **Given** the grammar printed in §4.1, **When** compared with the grammar the parser declares, **Then** the two are the same rule set (top rule `document = (line "\n")* line?`, `indent` matching spaces only, no `comment` rule, `key` as `[a-z][a-z0-9_-]*`, `ws` accepting spaces or tabs).
3. **Given** `SYML-SPEC-REVIEW.md`, **When** read, **Then** D20–D25 record the key pattern, text context, paragraph breaks, no comments, tab as separator, and strict indentation, each with the alternative not taken and a breaking-change note, and D5, D12, D13, D15, and D19 are annotated in place as superseded.
4. **Given** `CHANGELOG.md`'s 1.0.0 entry, **When** read by a 0.6.2 user, **Then** items 4, 7, 10, 12, 13, 16, and 17 describe what master does, and new items state that comments are gone (with the "loud for third-party files with `#` lines" warning), keys are `[a-z][a-z0-9_-]*`, values are text throughout, blank lines inside values are kept, indentless sequences are rejected, and a tab after a marker is separator whitespace.
5. **Given** the README, **When** read, **Then** a "Coming from YAML" section lists, in this order and each with its SYML spelling beside it: no comments; no `|`/`>` block-scalar indicators; no `---`/`...` document markers; no quoting; `null`, `true`, `123`, `~`, `[a, b]`, `{a: 1}` are plain strings; the key pattern; the `- key:` sibling-column rule (nested layout shown next to the sibling layout); blank lines inside a value are paragraph breaks.
6. **Given** §11.3, **When** compared with the package's exports, **Then** every class the spec says MUST exist is exported and every exported error class is listed (see FR-017 for the direction taken).
7. **Given** the release, **When** `git ls-remote --tags origin` is run, **Then** `1.0.0` is present and points at the commit that carries the revised spec, code, changelog, and README.
8. **Given** the public docs for `Source`, **When** read, **Then** they state that `Source` is not a `str`, that an empty `Source` is truthy, and that a multi-line `Source.text` is the dedented value `as_data()` returns.

---

### Edge Cases

- A root document whose first line is text is text throughout, so `hello\nk: v` is the root scalar `"hello\nk: v"` and `---\nk: v` is `"---\nk: v"`; a document whose first line is a key or list marker is structure, so `k: v\nhello` is still `OutOfContextNodeError`.
- A document containing only blank or whitespace-only lines loads as `""`; a document containing only former comment lines loads as their text (User Story 1, scenario 14).
- Blank-line retention counts physical blank lines one for one, whether they contain nothing or only spaces; a whitespace-only line contributes an empty line to the value, not its spaces.
- A NBSP-only line is a text line, not a blank line, so at root it is the scalar `"\xa0"` and inside a block value it is a below-baseline line (an error).
- A value made entirely of uppercase `KEY:` lines (`env:\n  HOME: /h`) is silent by design: it is a valid text value. Only the README explains it; no error fires.
- The key-pattern hint fires when the failing line or the line above it would be a key but for a character outside `[a-z][a-z0-9_-]*`; the same-column hint fires when the failing line is a list item at its key's column. Once FR-008 lands, a tab after a marker is valid, so the brainstorm's tab hint has no case left to fire on and is not required.
- `- key:` followed by `  - x` (item at the key's column) is an error under strict indentation even though the key came after a list marker; `- key:` followed by `    - x` is `[{"key": ["x"]}]`.
- `dumps` writes one space after `key:` and `-`; a leading tab in a value's first line is still unrepresentable (it would be a tab in indentation), and a leading space in a non-root first line is still unrepresentable (it would move the baseline).
- A value that ends with a newline (`"a\n"`) has no spelling, because trailing blank lines are inert; `dumps` raises for it.
- The recursion cliff is unchanged and documented, not fixed: a document nested a few hundred levels deep raises `RecursionError`, and the changelog states the measured depth rather than the ~500/~1000 it claims today (`syml-xreq.10`).
- `load()` on a handle whose `.name` is any `os.PathLike` uses it as the filename; `loads(b"k: v")` and `load()` on a closed handle raise a clear `TypeError` rather than leaking a builtin error that `except ValueError` would confuse with `ParseError`.
- `parse("\n").as_source().start` for a blank-only document reports a line and column consistent with its index (the former comment-only case in `syml-xreq.11` is now a root scalar and no longer zero-width).

## Requirements _(mandatory)_

### Functional Requirements

Each requirement names the brainstorm requirement it carries (R1–R17), the
`syml-xreq` findings it closes, and the review-document decision it supersedes
or affirms. "MUST" is normative for the shipped parser, serializer, and text.

- **FR-001** (R1; `syml-xreq.16`, `.17`): A mapping key MUST match exactly `[a-z][a-z0-9_-]*` (ASCII, leading letter), with nothing but indentation spaces before it. Any other would-be key line MUST lex as text. This replaces D15's White_Space exclusion and D19's no-uppercase rule and makes the `#`/`//` key exclusion of §11.2.3 moot (the class excludes them). `1:`, `_x:`, `-x:`, `e.mail:`, `名前:`, `ß:`, `URL:`, `firstName:` are text; `choice1:`, `first-name:`, `first_name:` are keys.
- **FR-002** (R2; `syml-xreq.16`): `dumps` MUST raise `UnrepresentableValueError` for any key outside FR-001's pattern, including the empty key, and §11.2.3 MUST state the pattern as the whole rule.
- **FR-003** (R3; `syml-xreq.22`): Once a value is text, every following line at or past its baseline MUST be a continuation of that value regardless of its shape (`- x`, `key: v`, `key:`, `# x`), until a line below the baseline ends it; a below-baseline line is re-offered as today. Structure MUST be lexed only at the first line of a bare `key:` or `-` block and at inline positions. A root document whose first line is text MUST be text throughout. This reverses D13 (and §5.1 rule 6); D11's baseline rule stands.
- **FR-004** (R4; `syml-xreq.15`): A blank or whitespace-only line between two continuation lines of the same value MUST be part of the value as an empty line (a paragraph break), one per physical blank line. Blank lines before the first continuation line, after the last, and between items or keys MUST stay inert, so a value never begins or ends with a blank line. This reverses D12 (and §5.1 rule 5).
- **FR-005** (R5; `syml-xreq.2`): A root scalar MUST keep its leading indentation and its baseline MUST be column 0: `  hello` loads as `"  hello"` and `  hello\nworld` as `"  hello\nworld"`, as §5.3 and changelog item 7 already say. The code changes; the spec does not.
- **FR-006** (R6; `syml-xreq.15`, `.22`, `.2`, `.6`): `dumps` MUST write every value FR-003 to FR-005 make loadable: paragraph breaks as blank lines in block form, later lines of any shape, and a root scalar with leading spaces in block form at column 0. Whether a line lexes as structure MUST be judged on the line's own characters without the §9.0 BOM strip, so a BOM-led line is content. The unrepresentable set of §11.2.1 MUST shrink to: a value whose first line lexes as structure at a list position (rule B) or at a block position (rule C); a non-root value whose first line begins with a space; a value whose first line begins with a tab; a value that begins or ends with a blank line; and control characters per rule D. The residual list is confirmed during planning (see Assumptions).
- **FR-007** (R7; `syml-xreq.21`): SYML MUST have no comments. A line beginning with `#` or `//` MUST be ordinary text wherever it appears, so a former comment line at a mapping's or list's own level is text at a container's level (an error per §6.4) and a document of only such lines is a root scalar. §4.3, §5.1 rule 4, the comment clause of §11.2.1, and every other reference to comments MUST be removed from the specification; the grammar's `comment` rule, the comment node, and the comment list on nodes MUST be removed from the implementation; `dumps` MUST write such lines.
- **FR-008** (R8; `syml-xreq.19`): A tab MUST be accepted as separator whitespace after `key:` and after `-`, in any mix with spaces, and a bare marker followed only by spaces or tabs MUST count as the bare marker (`a:\t` then a deeper block is `{"a": {...}}`). A tab in leading indentation MUST still raise `TabIndentationError`, and a tab after a value's first character is unchanged. `dumps` MUST still emit exactly one space. This reverses D5.
- **FR-009** (R9; `syml-xreq.1`, `.6`): Only U+0020 MUST count as indentation. Every other Unicode White_Space code point and every C0/C1 control at the start of a line MUST be content: an NBSP-led line keeps its NBSP, an NBSP-only line is a text line (not blank), a NBSP hides nothing from the tab scan because the tab is then not in leading indentation, and VT, FF, and NEL pass through verbatim per §4.6.1. `dumps` MUST refuse a value whose line starts with a non-ASCII space only if it would not read back identically, which under this rule is never. This affirms D9 and D14's spaces-and-tabs reading of leading whitespace.
- **FR-010** (R10; `syml-xreq.3`, `.20`): Children MUST be strictly deeper than their parent, list items included: `key:` followed by `- a` at the key's column MUST raise `OutOfContextNodeError`. The `- key:` inline-key sibling-column rule of §6.2 stands unchanged. `tests/fixtures/bar.syml` lines 23–24 MUST be re-indented past `when:` and the fixture's expected tree MUST remain the same. Changelog item 17 becomes true as written.
- **FR-011** (R11; `syml-xreq.18`): `str(ParseError)` MUST read `<filename>:<line>:<column>: <message>` followed by a newline and the offending line text, with the filename and its colon omitted when none is known; line and column follow §10.2 (1-indexed line, 0-indexed column). No new attribute and no grammar change is part of this requirement.
- **FR-012** (R12; `syml-xreq.17`, `.18`, `.3`): An out-of-context error message MUST name the column the failing line sits at and every column that was open during the walk-up, and MUST append a one-line hint when (a) the failing line or the line above it would have been a key but for FR-001's pattern, or (b) the failing line is a list item at its key's column (FR-010: "indent it past the key"). The hint stays in the message string; there is no reason code or expected-columns attribute.
- **FR-013** (R13; `syml-xreq.4`, `.5`): Every `ParseError` subclass MUST carry the filename prefix in `.message` when a filename is known (`OutOfContextNodeError` and `TabIndentationError` do not today), and every error position MUST be in the caller's original-text coordinates, through the BOM offset and the CRLF position map (the tab scan's position is normalized today). An empty-string filename MUST behave as no filename.
- **FR-014** (R14; `syml-xreq.23`): `dumps` MUST accept the output of `parse(text).as_source()` by reading `Source` keys and scalars as their text before any type check, so `dumps(parse(t).as_source())` round-trips. The public documentation MUST state that `Source` is not a `str`, that an empty `Source` is truthy and has no length, and that a multi-line `Source.text` is the dedented value `as_data()` returns. Making `Source` a `str` subclass is out of scope.
- **FR-015** (R15; `syml-xreq.24`, `.17`, `.20`): The README MUST gain a "Coming from YAML" section listing, in the order a YAML user trips over them, with the SYML spelling beside each: no comments; no block-scalar indicators; no document markers; no quoting; `null`, `true`, `123`, `~`, `[a, b]`, `{a: 1}` are strings; the FR-001 key rule (uppercase and camelCase keys are not SYML); the `- key:` sibling-column rule with the nested layout shown beside the sibling layout; and blank lines inside a value as paragraph breaks.
- **FR-016** (R16; `syml-xreq.3`, `.8`, `.9`, `.10`): The specification, the review document, and the changelog MUST describe exactly what ships. In `SYML-SPECIFICATION.md`: §4.1's grammar MUST be the grammar the code runs (the `document` top rule, `indent` as spaces only, `ws` as spaces or tabs, `key` as FR-001's class, no `comment` rule); §4.2, §4.5, §5.1, §5.3, §6, §7.5, §8.3, the §9.3 acceptance table, §11.2, and §11.3 MUST be revised for FR-001 to FR-010 and FR-017; §4.3 MUST be removed; §8.3's example MUST show the message the code produces. In `SYML-SPEC-REVIEW.md`: D20–D25 MUST record FR-001, FR-003, FR-004, FR-007, FR-008, and FR-010, each with the alternative not taken and a breaking-change note, and D5, D12, D13, D15, and D19 MUST be annotated as superseded in place. In `CHANGELOG.md`: items 4, 7, 10, 12, 13, 16, and 17 MUST be corrected (item 13 states the measured recursion depth), item 9 and item 11 MUST be true once FR-013 and FR-017 land, and each of FR-001, FR-003, FR-004, FR-007, FR-008, and FR-010 MUST appear as a breaking-change item, with the comments item warning that any third-party `.syml` file with `#` lines changes meaning.
- **FR-017** (R17; `syml-xreq.7`, `.11`, `.12`, `.13`, `.14`): The exception list and the P3 tail MUST be closed on paper and in code: §11.3 MUST list `EncodingError` as a `ParseError` and MUST demote `DocumentLimitError` from a required class to a name reserved for implementations that enforce §13.4 (no limit is enforced in this release, per Scope Boundaries); `dumps("")` MUST return the empty document `""`; non-`str` input to `loads` and a non-text `read()` result in `load` MUST raise a `TypeError` whose message names the expected type; `load()` MUST honour any `os.PathLike` `.name` as the filename; and the `Source` of a blank-only document ending in a newline MUST report a line and column consistent with its index.
- **FR-018** (release; handoff plan): The project version MUST remain `1.0.0`, the specification header MUST remain Version 1.0 with `syml` 1.0.0 as the conforming reference implementation, and the feature MUST end with the `1.0.0` tag created on the commit that carries all of the above and pushed to the remote. Building and uploading a distribution to PyPI is out of scope.

### Key Entities _(include if feature involves data)_

- **Text context** (new): the state a block or root position enters when its first own line is text. While it is open, every line at or past the value's baseline is that value's text whatever it looks like; a line below the baseline closes it. It is the one piece of tree-builder state this revision adds back.
- **Paragraph break** (new): an empty line inside a multi-line value, written as a physical blank line between two continuation lines and preserved one for one.
- **Key pattern** (revised): `[a-z][a-z0-9_-]*`; the whole rule for what may stand before a colon and be a key.
- **Separator whitespace** (revised): the run of spaces or tabs between `key:` or `-` and an inline value; a marker followed only by separator whitespace is bare.
- **Indentation** (revised): a run of U+0020 only; everything else at the start of a line is content.
- **Comment** (removed): no line is a comment; the entity and its node leave the model.
- **Error hint** (new): a trailing sentence in an out-of-context message that names the likely cause (a would-be key outside the key pattern; a list item at its key's column).
- **Unrepresentable set** (shrunk): the values `dumps` refuses, now limited to first lines that lex as structure at a list or block position, first lines beginning with a space (non-root) or tab, values beginning or ending with a blank line, control characters other than tab, and keys outside the key pattern.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Every one of the 24 `syml-xreq` children is closed, each with a reason naming the automated test that pins the repro from its description, and no open issue carries the `break-test` label.
- **SC-002**: The round-trip property (`loads(dumps(x)) == x` for every value `dumps` accepts, and `UnrepresentableValueError` for every value it refuses) passes over generated inputs with no excluded input family, including keys, paragraph breaks, structure-shaped later lines, leading non-breaking spaces, and indented root scalars.
- **SC-003**: Both repository fixtures load to their current expected trees, after the one same-column list in `bar.syml` is re-indented.
- **SC-004**: The lane-4 interactive-fiction and prose documents (`doc01_scene_cellar`, `doc01b_scene_taxi` with `Given:` lowercased, `doc03_prose`, `doc03b_prose_root`) load without error to the value the rulings give: paragraph breaks kept, dash-led and `Note:`-led lines kept as text, indented quotes kept with their indentation.
- **SC-005**: Every `**Output:**` and `**ERROR:**` example in the revised specification matches the implementation, and the grammar printed in §4.1 is the grammar the code declares, character for character in rule content.
- **SC-006**: All quality gates pass: the unit suite, the acceptance suite, the type checker, the linter, and the 100% coverage gate, with no new unreachable-branch exemption.
- **SC-007**: For each of the three hint cases (would-be key, same-column list, and a plain context error), a user reading `str(error)` sees the file, line, and column on the first line, the offending text on the second, and, for the first two, a hint naming the fix.
- **SC-008**: A YAML user reading the README section and the changelog can predict every one of the eight listed differences and every breaking change before hitting it; the `1.0.0` tag exists on the remote and the working tree is up to date with it.

## Assumptions

The following four items are carried verbatim from the brainstorm's "Deferred to
Planning" list and are to be settled during planning, not here:

- [Affects R3][Technical] How the tree builder carries "inside an open text
  value" state while keeping per-line lexing.
- [Affects R9][Technical] Adopting the spec's `document = (line "\n")* line?`
  top rule so `indent` can stop consuming `\n`. (Lane 2 verified that swapping
  `indent`'s character class without adopting the new top rule stalls the parse
  after line 1; the two changes land together.)
- [Affects R4][Technical] Whether pending blank lines are buffered in the
  parser or reconstructed from positions.
- [Affects R6][Technical] The exact residual unrepresentable set once R3, R4,
  R7 shrink §11.2.1. FR-006 states the expected list; planning confirms it
  against the revised grammar and edits §11.2.1 to match.

Additionally:

- **Spec before code.** Planning orders the work so `SYML-SPECIFICATION.md` and
  `SYML-SPEC-REVIEW.md` (D20–D25) are revised before any parser change, so the
  pinning tests are written from the revised spec. Under constitution principle
  IV as amended by spec 001, an open spec question may still be settled by a
  spec edit landing in the same commit as the behavior change that exposed it.
- **One implementation task per `syml-xreq` child** is the intended granularity
  for `/sp:05-tasks`; each task closes its child with a test that pins the
  repro from the issue description (the subagent-extracted repro table is
  reproduced in the issues themselves).
- **Ready-queue hazard for `/sp:05-tasks`.** The 24 `syml-xreq` children are
  open and unblocked, and this feature's epic links to them with `related`
  edges. The ralph drain scopes candidates by walking the epic's dependency
  tree, so those children may surface as ready leaves beside the tasks
  05-tasks creates. 05-tasks must either add a `blocks` dependency from each
  child on its pinning task or have the task close the child from inside; it
  must not let ralph claim a bare `syml-xreq` child as if it were a leaf task.
- **The lane-4 `AUTHOR` column is not the oracle.** It records a naive YAML
  user's expectation before the rulings; the expected value for any lane-4
  document is derived from FR-001 to FR-010 (see `reference/README.md` for the
  known divergences). Only the documents named in SC-004 are required to load
  as their author wrote them.
- **Tool names.** The round-trip property is expected to be run with
  Hypothesis, starting from `reference/lane-1-roundtrip-probe.py` (P1–P7) copied
  into `tests/` with its strategies updated for the revised language and its
  known-failure filter removed; the spec-example oracle is expected to be the
  lane-2 extractor rebuilt in the acceptance suite. Neither tool is a
  requirement; SC-002 and SC-005 are.
- **Tab hint is moot.** The brainstorm's R12 lists "has a tab after its
  marker" as a hint trigger; FR-008 makes that line valid, so the trigger has no
  input left and FR-012 lists only the two remaining cases.
- **`DocumentLimitError` direction.** FR-017 resolves the §11.3 conflict on the
  spec side (demote to a reserved name, add `EncodingError`) because Scope
  Boundaries keep limit enforcement out; the alternative (export an unused
  class) was rejected as an API promise with no behavior behind it.
- **Findings were re-executed on master `27a3e9a`** by the campaign orchestrator
  on 2026-09-24; a first planning step re-confirms the 24 repros still hold at
  the branch point.

## Scope Boundaries

Out of scope for this feature:

- **New syntax.** No quoting, no escapes, no block-scalar indicators, no
  document markers, no comments, no empty-container tokens. Anything not
  covered by a ruling stays as the 1.0 text says.
- **Limit enforcement.** No configurable limits and no `DocumentLimitError`
  enforcement beyond the paper reconciliation in FR-017; recursion and size
  limits stay documented (with the measured depth), not enforced, and the
  walk-up is not made iterative.
- **`Source` as a `str` subclass.** `Source` stays a non-`str` class; that
  change is a 1.x follow-up.
- **The earlier follow-ups `syml-xe9b.5`–`.7`.** They are not part of this
  revision; `.7` (the §13.4 performance note) may cite lane 2's timing table
  from the `syml-xreq` epic description when it is picked up.
- **Publishing to PyPI.** The feature ends at the pushed `1.0.0` tag.
- **The Dependabot alert** on the default branch (alert 8) is unrelated and
  untouched.
