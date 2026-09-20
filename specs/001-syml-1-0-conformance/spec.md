# Feature Specification: syml 1.0 — Full Conformance to the SYML Specification

**Feature Branch**: `001-syml-1-0-conformance`
**Created**: 2026-09-20
**Status**: Draft
**Input**: User description: "syml 1.0 spec conformance — make the shipped parser, serializer, error taxonomy, and source-tracking surface match `SYML-SPECIFICATION.md` in full, and leave `main` ready to release as 1.0.0."
**Brainstorm**: `specs/brainstorms/2026-09-14-syml-1.0-spec-conformance-requirements.md` (and its companion audit, `specs/brainstorms/2026-09-14-syml-1.0-spec-conformance-audit.md`)
**Beads Epic**: `syml-x0m`
**Beads Phase Tasks**:

- plan: `syml-x0m.1`
- red-team: `syml-x0m.2`
- tasks: `syml-x0m.3`
- analyze: `syml-x0m.4`
- implement: `syml-x0m.5`
- harden: `syml-x0m.6`

## Clarifications

### Session 2026-09-20

- Q: Should the requirements and audit brainstorm pair be used as the input for this specification? → A: Yes. The requirements doc's R1–R17 are the authoritative requirement list, and the audit's 21 verified gaps supply the acceptance scenarios.
- Q: Is publishing 1.0.0 to PyPI (tagging, building, uploading) in scope for this feature? → A: No. Publishing is a separate manual step taken after merge. The feature ends at a release-ready `main`: version bump, migration notes, and the spec relabelled 1.0.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Tree building follows the specification's acceptance rules (Priority: P1)

A configuration author writes a nested document and mis-indents one line. Today the
parser quietly re-parents it under a grandparent, or flattens the indentation of a
multiline value, and the author ships a config that means something other than what
it looks like. After this feature, indentation that does not exactly match a
registered sibling level is rejected, a key-value pair or list item that already
holds a value refuses further content, and a multiline value keeps the indentation
the author wrote.

**Why this priority**: Tree building is the largest cluster of divergences (five of
the audit's root causes) and it is the one where wrong behavior is silent — the
document parses, just not into what it looks like. Everything else in the feature
is either an error that is currently missing or an API that does not exist yet.

**Independent Test**: Feed the §4.2, §5.3, §6.2, §6.4, §7.6, §8.1, §8.3 and §9.3
examples through `loads` and assert the specified value or error, with no change to
quoting, pre-processing, or the serializer.

**Acceptance Scenarios**:

1. **Given** the document `parent:\n  child1: value\n child2: value`, **When** it is passed to `loads`, **Then** `OutOfContextNodeError` is raised (siblings must match on exact indentation, not "at least as deep").
2. **Given** the document `note: hello\n  more: text`, **When** it is passed to `loads`, **Then** `OutOfContextNodeError` is raised, because `note`'s pair is closed by its inline value.
3. **Given** the document `key:\n  first\n    indented\n  back`, **When** it is passed to `loads`, **Then** the result is `{"key": "first\n  indented\nback"}` — the block value's first own-line sets the baseline and indentation beyond it is preserved.
4. **Given** the document `key: a\nb`, **When** it is passed to `loads`, **Then** `OutOfContextNodeError` is raised, because `b` is not deeper than `key`.
5. **Given** the document `key: a\n    b\n  c`, **When** it is passed to `loads`, **Then** `OutOfContextNodeError` is raised: `b` fixes the baseline at 4, `c` falls below it, terminates the value, and finds no context when re-offered.
6. **Given** the root-scalar document `hello\n  world\nagain`, **When** it is passed to `loads`, **Then** the result is `"hello\n  world\nagain"` — the baseline is fixed at 0 and the two extra spaces survive.
7. **Given** the document `a:\n  b: 1\n  plain`, **When** it is passed to `loads`, **Then** `OutOfContextNodeError` is raised: plain text at a container's own level is not a value.
8. **Given** the document `-   name: Alice\n  role: admin` (three spaces after the marker), **When** it is passed to `loads`, **Then** `OutOfContextNodeError` is raised, because the inline key's own column — not the line's indentation — is the required column for its siblings.
9. **Given** the document `key: value1\nkey: value2`, **When** it is passed to `loads`, **Then** `DuplicateKeyError` is raised at the moment the second pair is incorporated, not when the result is materialized.
10. **Given** the document `a: Note\n  Big Warning: do not touch`, **When** it is passed to `loads`, **Then** the result is `{"a": "Note\nBig Warning: do not touch"}` — `Big Warning` is not a valid key, so the line joins as prose.

---

### User Story 2 - Pre-processing and line splitting match §9.0 and §13.3 (Priority: P1)

A user opens a document written on Windows, or exported with a byte-order mark, or
indented with tabs by an editor whose settings differ from their colleague's. Today
a BOM becomes part of the first key, carriage returns become part of values, and
tabs are silently expanded to four spaces so two files that look identical parse
differently. After this feature, the document is normalized exactly as §9.0
specifies, and a tab in indentation is a named, catchable error rather than a
silent reinterpretation.

**Why this priority**: Pre-processing runs before every other rule, so its
divergences contaminate the results of all the other stories; it is also the
cheapest cluster to close.

**Independent Test**: Pass documents carrying a BOM, CRLF, bare CR, tab
indentation, and `\u2028` through `loads` and assert the specified value or error.

**Acceptance Scenarios**:

1. **Given** a document whose first character is a byte-order mark followed by `key: value`, **When** it is passed to `loads`, **Then** the result is `{"key": "value"}` — exactly one leading mark is stripped.
2. **Given** a document consisting only of a byte-order mark, **When** it is passed to `loads`, **Then** the result is `""`.
3. **Given** the document `a: b\r\nc: d`, **When** it is passed to `loads`, **Then** the result is `{"a": "b", "c": "d"}`; the same holds for `a: b\rc: d` with a bare carriage return.
4. **Given** the document `\tkey: value`, **When** it is passed to `loads`, **Then** `TabIndentationError` is raised.
5. **Given** the document `key: a\n\tb`, **When** it is passed to `loads`, **Then** `TabIndentationError` is raised — a continuation line gets no exemption.
6. **Given** a document whose only content is spaces and a tab on one line, **When** it is passed to `loads`, **Then** no error is raised: a whitespace-only line is blank and is discarded before the tab check.
7. **Given** the document `a: b\u2028c\nx: y`, **When** it is passed to `loads`, **Then** the result is `{"a": "b\u2028c", "x": "y"}` — the separator stays inside the value, because only `\n` terminates a line.

---

### User Story 3 - Lines lex per the §4.1 grammar as printed (Priority: P1)

An author writes a bare list marker with the item on the next line, or a value with
no space after the colon, or a negative number at the start of a line. Today some
of these raise an incomplete-parse error from inside the parsing machinery and
others produce the wrong shape. After this feature each line lexes exactly as the
printed grammar says: structural forms require their guard, and anything that is
not a complete structural form falls through to scalar text.

**Why this priority**: Lexing decides what every later rule is even operating on;
the fallthrough rule (§7.6) is the language's central predictability promise.

**Independent Test**: Pass the §4.6, §7.5, §7.6, §4.4 and §4.5 examples through
`loads` and assert the specified value or error.

**Acceptance Scenarios**:

1. **Given** the document `-\n  block item`, **When** it is passed to `loads`, **Then** the result is `["block item"]`.
2. **Given** a document consisting of a hyphen followed by one space and nothing else, **When** it is passed to `loads`, **Then** the result is a list holding one empty-string item.
3. **Given** the document `key:value`, **When** it is passed to `loads`, **Then** the result is the scalar `"key:value"`, with no exception raised.
4. **Given** the document `-item`, **When** it is passed to `loads`, **Then** the result is the scalar `"-item"`; likewise `-42` yields `"-42"`.
5. **Given** the document `key:\tv` (tab immediately after the colon), **When** it is passed to `loads`, **Then** the result is the scalar `"key:\tv"` — a tab is never separator whitespace.
6. **Given** the document `key: \tv` (space then tab after the colon), **When** it is passed to `loads`, **Then** the result is `{"key": "\tv"}` — the tab is preserved as value content.
7. **Given** a document whose first line is `key:` followed by one trailing space and whose second line is `  nested: content`, **When** it is passed to `loads`, **Then** the result is `{"key": {"nested": "content"}}`, identical to the no-trailing-space form.
8. **Given** the document `a:\n<eight spaces>\n  b: c\n  d: e` where the second line is whitespace only, **When** it is passed to `loads`, **Then** the result is `{"a": {"b": "c", "d": "e"}}` — the whitespace-only line never affects indentation.
9. **Given** the document `a\x01b: v`, **When** it is passed to `loads`, **Then** the line does not lex as a key-value pair, because keys exclude control characters and the Unicode whitespace set.

---

### User Story 4 - Absent values are the empty string, never a null (Priority: P1)

A user reads a section header, an empty document, or a comment-only document.
Today those come back as a language-level null, which every caller must special-case
and which contradicts the library's one promise: every leaf value is a string.

**Why this priority**: This is the library's stated reason to exist. It is a small
change with an outsized effect on every downstream caller's type handling.

**Independent Test**: Pass empty, comment-only, and section-header documents
through `loads` and assert the result contains only strings, lists, and mappings.

**Acceptance Scenarios**:

1. **Given** the document `empty:\nnext: value`, **When** it is passed to `loads`, **Then** the result is `{"empty": "", "next": "value"}`.
2. **Given** the empty document, **When** it is passed to `loads`, **Then** the result is `""`.
3. **Given** the document `# just a comment`, **When** it is passed to `loads`, **Then** the result is `""`.
4. **Given** a document whose line is `key:` followed by one trailing space and nothing else, **When** it is passed to `loads`, **Then** the result is `{"key": ""}`.
5. **Given** any document accepted by `loads`, **When** the result is walked to its leaves, **Then** no leaf is a null of any kind.

---

### User Story 5 - A complete, catchable error taxonomy and a stable entry API (Priority: P1)

An application embeds `syml` and wants to report parse problems to its own users. It
needs to catch a single base class, distinguish the failure kinds, and read the
position and offending line off the exception. It also wants to hand `load` whatever
file handle it already has, text or binary, and be told clearly when the bytes are
not valid UTF-8.

**Why this priority**: Without this, callers cannot catch the library's failures
safely at all — an exception type from a third-party parsing dependency escapes
today — and the other stories' new errors have nowhere to live.

**Independent Test**: Assert the seven exported classes and their inheritance,
assert each exception's named attributes on a triggering input, assert that no
non-`ParseError` exception escapes the documented malformed inputs, and call `load`
with both a text handle and a binary handle.

**Acceptance Scenarios**:

1. **Given** the installed library, **When** `ParseError`, `OutOfContextNodeError`, `DuplicateKeyError`, `TabIndentationError`, `MalformedQuotedStringError`, `UnrepresentableValueError`, and `EncodingError` are imported from `syml`, **Then** all seven resolve and their inheritance matches §11.3 as amended.
2. **Given** the document `key:value` — which today escapes as an incomplete-parse exception from the parsing dependency — **When** it is passed to `loads`, **Then** it parses successfully; and **Given** any document in the audit's failing set, **When** it is passed to `loads`, **Then** any exception raised is a `ParseError` and no third-party parser exception escapes.
3. **Given** a document that raises any `ParseError`, **When** the exception is inspected, **Then** `.message`, `.position`, and `.line_text` are readable as named attributes.
4. **Given** the document `key: value1\nkey: value2`, **When** `DuplicateKeyError` is caught, **Then** it also carries the repeated key and the first occurrence's position.
5. **Given** a binary file handle over valid UTF-8 SYML, **When** it is passed to `load`, **Then** it parses to the same result as the equivalent text handle.
6. **Given** a binary file handle over bytes that are not valid UTF-8, **When** it is passed to `load`, **Then** `EncodingError` is raised and no replacement characters or unpaired surrogates appear in any result.

---

### User Story 6 - Quoted strings work exactly where §4.7 says they do (Priority: P2)

An author needs a value with leading spaces, an embedded newline, or a literal
backslash. Quoting is the only way to write those, and today it does not exist at
all: the quote characters end up in the value. The author also needs the opposite
guarantee — that an apostrophe at the start of a bare prose line stays prose.

**Why this priority**: Quoting is a whole missing feature and the largest single
gap, but every document that avoids quotes parses correctly without it, so it ranks
below the rules that silently mis-shape ordinary documents.

**Independent Test**: Pass the §4.7 and §8.5 examples through `loads` and assert
the decoded value or `MalformedQuotedStringError`, plus the bare-line cases that
must not decode.

**Acceptance Scenarios**:

1. **Given** the document `padded: "  hello  "`, **When** it is passed to `loads`, **Then** the result is `{"padded": "  hello  "}`.
2. **Given** the document `literal: 'hello\\nworld'` written with a literal backslash-n inside single quotes, **When** it is passed to `loads`, **Then** the value is the twelve characters `hello\nworld`, backslash and `n` intact, not a newline.
3. **Given** the document `with_quote: 'it''s fine'`, **When** it is passed to `loads`, **Then** the value is `it's fine`.
4. **Given** the document `escaped: "hello\nworld"` using the escape sequence, **When** it is passed to `loads`, **Then** the value contains a real line feed.
5. **Given** the document `key: "unterminated`, **When** it is passed to `loads`, **Then** `MalformedQuotedStringError` is raised.
6. **Given** the document `key: "a" trailing`, **When** it is passed to `loads`, **Then** `MalformedQuotedStringError` is raised.
7. **Given** the documents `k: "a\xb"`, `k: "\ud800"`, and `k: "\U00110000"`, **When** each is passed to `loads`, **Then** each raises `MalformedQuotedStringError` — invalid escape, surrogate code point, and code point above the Unicode maximum.
8. **Given** the document `key: "a"\n  b`, **When** it is passed to `loads`, **Then** `OutOfContextNodeError` is raised: a quoted value is complete and accepts no continuation.
9. **Given** the root-scalar document `"unterminated`, **When** it is passed to `loads`, **Then** the result is the literal text including the leading quote character — quoting is not recognized on a bare line.
10. **Given** the document `key: He said\n  'yes'`, **When** it is passed to `loads`, **Then** the result is `{"key": "He said\n'yes'"}` — the continuation line does not quote-decode.

---

### User Story 7 - Round-trip serialization with `dumps` and `dump` (Priority: P2)

A tool that reads a SYML config, edits a value, and writes it back needs a
serializer. Today none exists, so every such tool hand-rolls one and produces output
the parser reads back differently.

**Why this priority**: A 1.0 that cannot round-trip is a half-conforming 1.0, but
it is additive: no existing caller breaks while it is missing.

**Independent Test**: Assert `loads(dumps(x)) == x` over a corpus of representable
values, and assert `UnrepresentableValueError` over the §11.2.2–§11.2.4 cases.

**Acceptance Scenarios**:

1. **Given** any representable value `x`, **When** it is serialized with `dumps` and re-read with `loads`, **Then** the result equals `x`.
2. **Given** a string with leading or trailing whitespace, or containing a line feed, a carriage return, or another control character, **When** it is serialized, **Then** it is emitted quoted, and a line feed is emitted as an escape rather than as block continuation.
3. **Given** a value that needs quoting and holds no control characters, **When** it is serialized, **Then** single-quoting is used in preference to double-quoting.
4. **Given** a list item whose value is a mapping, **When** it is serialized, **Then** exactly one space separates the marker from the key.
5. **Given** a mapping, **When** it is serialized, **Then** its keys appear in insertion order.
6. **Given** a structure containing an empty list or an empty mapping at any depth, **When** it is serialized, **Then** `UnrepresentableValueError` is raised rather than the value being omitted or emptied.
7. **Given** a key containing whitespace or a colon, the empty-string key, or a key beginning with `#` or `//`, **When** it is serialized, **Then** `UnrepresentableValueError` is raised.
8. **Given** a root scalar that would lex as structure, begins with a comment marker, holds a control character, has leading or trailing whitespace on a line, or is exactly two quote characters, **When** it is serialized, **Then** `UnrepresentableValueError` is raised.
9. **Given** a value written to an open file handle with `dump`, **When** that file is read back with `load`, **Then** the result equals the original value.

---

### User Story 8 - Source tracking is a supported surface with original-text positions (Priority: P2)

An editor integration parses a document, gets a value back, and wants to place a
cursor on the exact character the value came from — in the file as the user has it
on disk, carriage returns, byte-order mark and all. Today source tracking works but
is untested and exempted from the coverage gate, and its positions refer to the
normalized text, so they drift from the real file.

**Why this priority**: Source tracking is the reason the node tree is public at all,
but it is an optional feature in the specification and no current caller depends on
the exact coordinates.

**Independent Test**: Parse documents containing a byte-order mark, CRLF, and
`\u2028`, then assert that each reported position indexes the corresponding
character in the caller's original text.

**Acceptance Scenarios**:

1. **Given** a document parsed with source tracking, **When** `as_source()` is called on the tree, **Then** every leaf is a `Source` carrying a filename and start and end `Pos` values, and `as_data()` returns the equivalent plain strings, lists, and mappings.
2. **Given** a document whose first character is a byte-order mark, **When** a value's position is read, **Then** its index, line, and column locate that value in the original text, counting the mark.
3. **Given** a document using CRLF line endings, **When** a value's position is read, **Then** its index locates that value in the original text, counting each carriage return.
4. **Given** the document `a: b\u2028c\nx: y`, **When** `x`'s position is read, **Then** it reports line 2.
5. **Given** the released library, **When** the source-tracking surface is exercised, **Then** it is covered by tests rather than exempted from the coverage gate.

---

### User Story 9 - A release-ready `main` with migration notes and one conformance ledger (Priority: P3)

A 0.6.2 user upgrading to 1.0.0 opens the migration notes and finds every behavior
change that can bite them, in one place. A contributor opening the repository finds
one statement of where the parser stands against the specification, not two
documents that disagree.

**Why this priority**: It is the last step and depends on every other story being
finished, but nothing ships responsibly without it.

**Independent Test**: Read the migration notes against the audit's gap list and
confirm every user-visible change is listed; confirm the project version metadata,
the specification header, and the repository's guidance documents all say 1.0.

**Acceptance Scenarios**:

1. **Given** the repository at the end of this feature, **When** the project version metadata is read, **Then** it declares `1.0.0`.
2. **Given** `SYML-SPECIFICATION.md`, **When** its header is read, **Then** it is labelled version 1.0 and names `syml` 1.0.0 as the conforming reference implementation, with the review pass folded into a single version-history entry.
3. **Given** the migration notes, **When** a 0.6.2 user reads them, **Then** they list the null-to-empty-string change, tabs and duplicate keys becoming errors, quoted values decoding (including apostrophe-initial inline values becoming errors), the leading-marker and `key:value` fallthrough, third-party parser exceptions no longer escaping, the new `load` input types, and the new `dumps` and `dump`.
4. **Given** the repository, **When** it is searched for a conformance ledger, **Then** exactly one exists: `todo.txt` is retired or rewritten and `CLAUDE.md`'s "Spec vs. implementation" section says the parser conforms.
5. **Given** a fresh environment, **When** `syml` is imported, **Then** no warning is emitted.
6. **Given** the node-tree test module, **When** it is inspected, **Then** it holds real tests rather than being empty, and the dead statement in `Source`'s concatenation operator is gone.
7. **Given** the constitution, **When** principle IV is read, **Then** it no longer claims the specification is aspirational or that `todo.txt` is the conformance ledger, it permits a specification edit that lands in the same commit as the behavior change it exposed, and the constitution version is bumped per its own Governance Amendment Procedure and Versioning Policy.
8. **Given** the plan's Constitution Check section, **When** it is read, **Then** it lists `Pos` moving to original-text coordinates, `load()` accepting binary streams, and the resulting 1.0.0 major version bump, each paired with the non-breaking alternative it rejected.
9. **Given** the repository at the end of this feature, **When** it is inspected for release artifacts, **Then** no `1.0.0` tag exists and no distribution has been built or uploaded.

---

### Edge Cases

- **Nesting deeper than the host language's recursion limit**: documents nested past roughly 500 levels raise the host's own recursion error rather than a SYML error. The §13.4 implementation limits — maximum depth, line length, and document size — and the `DocumentLimitError` class that reports them are deferred past 1.0; §11.3 and §13.4 are edited to mark them post-1.0, and the recursion behavior is recorded as a documented known limitation rather than a defect.
- **`DocumentLimitError` is not part of the 1.0 error surface.** The seven exported classes are the complete list; a caller must not expect an eighth.
- **Fixtures that depend on trailing whitespace** (`key:` plus a space, a marker plus a space, and the §7.5 preservation cases) cannot be stored as literal file content, because the repository's commit hooks strip trailing whitespace. They are constructed programmatically.
- **Duplicate keys nested inside another mapping**: `p:\n  a: 1\n  a: 2` raises `DuplicateKeyError` exactly as at the top level; detection is per mapping, at incorporation.
- **A document containing only a byte-order mark** is the empty document and yields `""`, not a one-character scalar.
- **A quoted value followed by a more-indented line** is not a continuation: the quoted value is complete, the following line is re-offered up the tree, and the owning node being closed, it raises `OutOfContextNodeError`.
- **`#tag: value` is a comment**, not a key named `#tag`; the comment rule wins over the key rule regardless of what follows. This already holds and must keep holding.
- **A second byte-order mark immediately after the first** is ordinary content and is preserved verbatim.
- **A tab-only line** is blank and is discarded before the tab-in-indentation check, so it raises nothing.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: Every fenced `syml` block in `SYML-SPECIFICATION.md` that states an Output MUST produce exactly that output from `loads`, and every block that states an ERROR MUST raise the named error.
- **FR-002**: The system MUST apply §9.0 pre-processing before any grammar rule sees a line: strip exactly one leading byte-order mark; replace every CRLF and every remaining bare CR with a line feed; treat a byte-order-mark-only document as the empty document; and raise `TabIndentationError` when a tab appears anywhere in the leading indentation of a non-blank line (whitespace-only lines are blank and are discarded first). A tab after `key:` or after a list marker MUST be value content, never separator whitespace.
- **FR-003**: The system MUST split lines on U+000A only. U+2028, U+0085, U+000B, U+000C and every other Unicode line or paragraph separator MUST NOT terminate a line, for tokenization, position tracking, or error line numbering alike.
- **FR-004**: Structural lines MUST lex per the §4.1 grammar as printed: a bare list marker takes a block value; a marker followed by a space and nothing else is an empty list item; `key:value` and `-item` fall through to scalar text per §7.6; `key:` followed by a trailing space behaves identically to `key:` (D6); whitespace-only lines are blank and never affect indentation; and keys exclude the Unicode `White_Space` set and control characters (D15).
- **FR-005**: Empty values, empty documents, and comment-only documents MUST yield `""`. No result of `loads` or `load` may contain a null at any depth.
- **FR-006**: Tree building MUST follow §9.3 and §5.3: siblings match on exact indentation; a key-value pair or list item that already has a child is closed to all further content; a multiline value's baseline is set by its first own-line (D11) and indentation beyond the baseline is preserved; a line below the baseline terminates the value and is re-offered up the tree (B5); plain text at a container's own level is an error (M24); an inline key after a list marker sets the sibling column (M23); blank and comment lines inside a value are skipped (D12); and a continuation-position line that lexes as structure is structure (D13).
- **FR-007**: Duplicate keys within one mapping MUST raise `DuplicateKeyError` at incorporation time, comparing keys by code point, and MUST NOT fall through to the walk-up.
- **FR-008**: Quoted strings MUST behave per §4.7 and D2/D3: recognized only inline after `key:` or a list marker; single-quoted literally with `''` as the embedded-quote escape; double-quoted with the §4.7 escape table; a quoted value ends its line and accepts no continuation; and unterminated quotes, trailing text after the closing quote, invalid escapes, surrogate code points, and code points above U+10FFFF MUST raise `MalformedQuotedStringError`. Bare lines MUST never quote-decode.
- **FR-009**: `syml` MUST export exactly seven error classes — `ParseError`, `OutOfContextNodeError`, `DuplicateKeyError`, `TabIndentationError`, `MalformedQuotedStringError`, `UnrepresentableValueError`, and a new `EncodingError` (a `ParseError`, added to §11.3, which is open) — with the inheritance §11.3 states as amended. No exception from a third-party parsing dependency may escape `loads` or `load`. Every `ParseError` MUST expose `.message`, `.position`, and `.line_text` as named attributes.
- **FR-010**: `load()` MUST accept either a text stream or a binary stream. Binary input MUST be decoded as strict UTF-8, and invalid bytes MUST raise `EncodingError` rather than producing replacement characters or unpaired surrogates.
- **FR-011**: `dumps(value)` and `dump(value, fp)` MUST exist and follow §11.2: the §11.2.1 quoting table, exactly one space after a list marker before an inline key, no block continuation for embedded line feeds, insertion-order keys (D8), and `UnrepresentableValueError` for the empty list, the empty mapping, unrepresentable keys (D1, M8), and root scalars per §11.2.4 (D17). `loads(dumps(x))` MUST equal `x` for every representable `x`.
- **FR-012**: `as_source()`, `Source`, and `Pos` MUST be a supported, documented, fully tested 1.0 surface, and the blanket unreachable-branch exemptions over the node-tree module MUST be removed.
- **FR-013**: `Pos` index, line, and column MUST refer to the caller's original text, before byte-order-mark stripping and line-ending normalization, so that an editor integration can point at the real character.
- **FR-014**: The release text MUST be updated: the project version metadata becomes `1.0.0`; `SYML-SPECIFICATION.md`'s header is relabelled version 1.0 with a status line naming `syml` 1.0.0 as the conforming reference implementation and its version history folded into one 1.0 entry; and `SYML-SPEC-REVIEW.md`'s subject line is updated to match. The constitution's principle IV is updated under FR-019.
- **FR-015**: Migration notes (in the changelog or the README) MUST list every user-visible behavior change from 0.6.2: nulls becoming `""`; tabs in indentation and duplicate keys becoming errors; quoted values decoding, and apostrophe-initial inline values becoming errors; the leading-marker and `key:value` fallthrough; third-party parser exceptions no longer escaping; the new `load()` input types; and the new `dumps` and `dump`.
- **FR-016**: `todo.txt` MUST be retired or rewritten so the repository holds exactly one conformance ledger, and `CLAUDE.md`'s "Spec vs. implementation" section MUST be rewritten to state that the parser conforms.
- **FR-017**: Hygiene MUST be closed: the node-tree test module is populated (its untracked backup folded in or deleted), the dead statement in `Source`'s concatenation operator is removed, and importing `syml` emits no warning.
- **FR-018**: The feature MUST end at a release-ready `main` — version bump, migration notes, and relabelled specification — and MUST NOT include tagging, building, or uploading a distribution to PyPI, which is a separate manual step taken after merge.
- **FR-019**: The constitution's principle IV MUST be amended and the constitution version bumped per its own Governance Amendment Procedure and Versioning Policy. The amendment MUST: drop the stale claims that the specification is aspirational and that `todo.txt` is the conformance ledger (both false once FR-014 and FR-016 land); and relax the "an open spec question MUST be settled before implementing against it" clause for this feature, so the implementer may edit specification text when implementation exposes a defect, provided the edit lands in the same commit as the behavior it changes. The release-text half of the relabel is FR-014.
- **FR-020**: The plan's Constitution Check section MUST list, per principle VI, every breaking change to the semver-guarded public surface together with the non-breaking alternative it rejected: `Pos` semantics moving to original-text coordinates (FR-013), `load()` accepting binary streams (FR-010), and the resulting major version bump to 1.0.0.

### Key Entities _(include if feature involves data)_

- **Document**: the caller's original text, plus the normalized text produced from it by pre-processing. Positions reported to callers refer to the original; every parsing rule operates on the normalized form.
- **Line**: one physical line of the normalized document, terminated by a single line feed. Each line carries its own indentation level and lexes independently of its neighbours into exactly one of: blank, comment, structure, or scalar text.
- **Node tree**: the parsed shape of a document. A single **root** holds one value; a **mapping** holds key-value pairs at one shared level; a **list** holds list items at one shared level; a **key-value pair** and a **list item** each hold at most one value and are closed once they do; a **text leaf** holds a scalar value and carries the anchor level and baseline that decide which later lines join it. Every leaf is a string.
- **Source**: a leaf value carrying its text plus the filename and the start and end positions it came from; it compares and hashes by text so it is interchangeable with a plain string.
- **Pos**: a position in the caller's original text, as an index, a line number, and a column number, counted in code points.
- **Error hierarchy**: `ParseError` (a `ValueError`) as the single catchable base for every parsing failure, carrying a message, a position, and the offending line; `OutOfContextNodeError`, `DuplicateKeyError`, `TabIndentationError`, `MalformedQuotedStringError`, and `EncodingError` as its subclasses; and `UnrepresentableValueError`, raised by serialization rather than parsing, outside the `ParseError` hierarchy.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Every specification example that states an Output or an ERROR runs as an automated acceptance scenario and passes — 53 today, and the count tracks the specification as it is edited.
- **SC-002**: The D1–D17 probe inputs from the review's verification record — a quoted value followed by a continuation line, a blank line inside a value, a tab-only line, a list marker with three spaces before an inline key, a surrogate escape, a non-breaking space in a key, and `\u2028` inside a value — all behave exactly as the specification says.
- **SC-003**: `loads(dumps(x))` equals `x` for every representable `x` in the round-trip corpus, and every value outside that set raises `UnrepresentableValueError`.
- **SC-004**: All quality gates pass — the full test suite, the acceptance suite, the type checker, the linter, and the 100% coverage gate — with no unreachable-branch exemption beyond what constitution principle III permits, and specifically none over the source-tracking surface.
- **SC-005**: No exception that is not a `ParseError` escapes `loads` or `load` for any input in the audit's corpus or the acceptance suite, other than documents beyond the documented nesting limitation (see Edge Cases), and each of the seven exported error classes is raised by at least one scenario.
- **SC-006**: A 0.6.2 user reading the migration notes can predict every behavior change they will hit: every user-visible change in the audit's gap list appears there.
- **SC-007**: Importing the library emits no warning, and the repository contains exactly one conformance ledger.

## Assumptions

The following six items are carried verbatim from the requirements brainstorm's
"Deferred to Planning" list and are to be settled during planning, not here:

- [Affects R4][Technical] D15's `White_Space` set vs Python `re`'s `\s`
  (which also matches U+001C–U+001F) vs §4.1's key class excluding
  `\x00-\x1f`: which rule rejects `key\x1cname: v`, and as scalar fallthrough
  or error? Spec is open; settle and edit.
- [Affects R13][Technical] Mechanism for mapping normalised-text positions back
  to original positions (offset table vs parsing the original with a
  CR-tolerant grammar).
- [Affects R9][Technical] Exact attribute shape of `.position` (a `Pos`? line
  number?) and which errors carry `line_text`.
- [Affects R1][Needs research] Fixture strategy for examples with trailing
  spaces (`key: `, `- `, §7.5 preservation): the pre-commit
  `trailing-whitespace` hook strips them from files, so these must be built
  programmatically in tests.
- [Affects R11][Technical] Whether `dumps` output format for nested structures
  (indent width, blank lines between top-level keys) is fixed by the spec or
  an implementation choice to document.
- [Affects R12][Technical] Whether `Source` keys colliding on text
  (`Source.__eq__`/`__hash__` by text) needs any change now that duplicate
  keys are detected before materialisation (m4).

Additionally:

- Whether the acceptance suite extracts the specification's `syml` blocks at test
  time or hand-transcribes them into Gherkin is a planning decision, not a
  requirement of this specification. Either satisfies SC-001.
- `EncodingError`'s place in the hierarchy is not stated in the specification.
  §11.1 permits "a `ParseError` (or a clearly-documented decoding exception
  callers can distinguish from a successful parse)". This specification adopts the
  plain reading — `EncodingError` is a `ParseError` — and §11.3 gains the entry
  under FR-009. Planning may revisit it only by editing §11.3 explicitly.
- The §4.1 grammar as printed, and the shape of the reference tree builder written
  during the specification review, are available as starting points rather than
  things to re-derive; both are characterized, with their per-area gap lists, in
  `specs/brainstorms/2026-09-14-syml-1.0-spec-conformance-audit.md`.
- The audit's findings were taken at commit `2bfd6e6` against version 0.6.2; a
  first planning step re-confirms they still hold.

## Scope Boundaries

Out of scope for this feature:

- **The §13.4 implementation limits** — maximum nesting depth, maximum line
  length, maximum document size — and the `DocumentLimitError` class that reports
  them. The deep-nesting recursion failure stays and is documented as a known
  limitation; §11.3's class list and §13.4 are edited to mark limits as post-1.0.
- **Any v1.2 syntax**: no `[]` or `{}` empty-collection tokens, no quoted keys, no
  surrogate-pair combining, no error for a tab after a structural marker. Values
  needing them stay unrepresentable and `dumps` raises.
- **Root-scalar quoting.** D17 stands: `dumps` raises rather than gaining a new
  grammar rule for the root position.
- **A deprecation or bridge release, and any compatibility flags.** The break from
  0.6.2 is clean and documented.
- **Publishing to PyPI.** Tagging, building, and uploading the 1.0.0 distribution
  are a manual step after this feature merges.
