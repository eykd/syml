Changelog
=========

## 1.0.0 (2026-09-25)

Migration notes for a 0.6.2 user upgrading to 1.0.0. Every user-visible
change from 0.6.2 is listed below, numbered to match Contract 06's audit
(`specs/002-syml-language-revision/contracts/06-release-text.md` § FR-016
and its predecessor, `specs/001-syml-1-0-conformance/contracts/09-release-text.md`
§ FR-015). Items 19-24 record the 2026-09-24 D20-D25 language revision, items
25-26 the 2026-09-25 D26/D27 break-testing-round-2 hint additions (see
`SYML-SPEC-REVIEW.md`); items 1-18 cover everything else changed in this one
1.0.0 release.

1. Absent values: `None` → `""`, at every depth.
2. Tabs in indentation → `TabIndentationError`.
3. Duplicate keys → `DuplicateKeyError`.
4. Keys must match exactly `[a-z][a-z0-9_-]*` — lowercase ASCII letters,
   digits, `_`, and `-` only; no uppercase letter and no other punctuation
   (D20). `Name: x`, `firstName: x`, `URL: x`, `1: x`, `e.mail: x`, and
   `名前: x` are no longer mappings: `Name: x` is now the scalar text
   `Name: x` — breaking vs 0.6.2, and **silent** for a one-line document.
   In a mapping it raises instead: `name: a\nName: b` is
   `OutOfContextNodeError`, because the second line is text at a mapping's
   level. Inside a list item the effect is asymmetric: a non-pattern
   **first** key silently makes the whole item one string:
   `- containerPort: 80\n  protocol: TCP` was
   `[{'containerPort': '80', 'protocol': 'TCP'}]` in 0.6.2 and is now
   `["containerPort: 80\nprotocol: TCP"]`, with no error either version.
   A non-pattern **later** key, by contrast, now raises with a hint.
   Rename such keys to lowercase (`name:`). `dumps({'Name': 'x'})`
   raises `UnrepresentableValueError`. Quoted strings remain unsupported,
   as in 0.6.2 (D18): a leading `'` or `"` is ordinary text everywhere, and
   `title: "Hello"` is the value `"Hello"` with its quotation marks, just
   as it was.
5. `-` / `key:value` fallthrough: bare `-` takes a block value;
   `key:value` is a scalar instead of raising.
6. Sibling indentation is now exact (`==`), and a closed key/item accepts
   nothing.
7. Multiline values preserve indentation past the baseline; a
   below-baseline line terminates the value. A root scalar's baseline is
   column 0, so an indented root scalar keeps its indentation: `  hello`
   was `'hello'` and is `'  hello'`; `  hello\nworld` is
   `'  hello\nworld'`.
8. Parsimonious exceptions no longer escape; everything is a `ParseError`.
9. `ParseError` gains `.message` / `.position` / `.line_text`, and its
   constructor now requires them: `ParseError('msg')` (valid in 0.6.2,
   where it was a bare `ValueError`) is a `TypeError`. `.message` is
   prefixed with the filename when there is one. `str(e)` renders
   `<filename>:<line>:<column>: <description>\n<line_text>`, with the
   `<filename>:` segment omitted when no filename is known — e.g.
   `syml.loads('a: b\nc')` raises with `str(e)` starting `2:0: Line 2, at
   column 0, is a text line, ...` followed by the offending line.
10. `Pos` coordinates now refer to the **original** text. `Source` still
    equals a `str` with the same text, but no longer equals a non-`str`
    (`Source.from_text('1') == 1` was `True`). `Source.from_node` takes
    `(pnode, filename=None)`; `Pos.from_str_index` and `Source.from_text`
    count only `\n` as a line break (U+2028, U+0085 and the rest no longer
    start a line); and `Source + str` now counts the joining `\n` in
    `end.index` and accepts `''`.
11. `load()` accepts binary streams and decodes them as strict UTF-8;
    invalid UTF-8 → `EncodingError`. A text handle decodes with its own
    codec before `load` sees the text: a failure there is also
    `EncodingError`, but a handle in another encoding can decode UTF-8
    bytes to the wrong characters with no error (cp1252 reads `é` as `Ã©`),
    so strict UTF-8 needs `open(p, 'rb')` or `encoding='utf-8'`. `filename`
    now defaults to a `str` or path-like `file_obj.name`. `loads(bytes)`
    (as opposed to `load`) is a `TypeError`: it only accepts `str`.
    `Pos.index` from a default `open(p)` text handle is an offset into
    newline-translated text; editor-grade positions need `open(p, 'rb')`
    or `open(p, encoding='utf-8', newline='')`.
12. New: `dumps`, `dump`, and `parse` promoted to a public export.
    `dumps` writes every string as literal text: a single-line value
    inline, a multi-line string (and any root scalar) in block form with
    each line indented beneath its key or `-`; `dumps('')` is `''`. It
    raises `UnrepresentableValueError` for the nine families in §11.2.1:
    a control character other than LF/TAB anywhere; a structure-shaped
    first line at a list position (any length), at a mapping position
    (multi-line only), or at the root (any length), plus any later line
    whose leading `- ` marker chain holds more than 32 markers; a value's
    first line, inline or block, beginning with a space (mapping or list
    position only; a root scalar's leading spaces round-trip literally);
    any line whose leading run of spaces/tabs contains a tab; a
    non-empty, spaces-and-tabs-only line; a
    multi-line value whose first or last line is empty; a mapping key that
    does not match `[a-z][a-z0-9_-]*`; an empty list or empty mapping at
    any depth; and a root scalar with any line beginning with `#` or `//`.
    Single-line mapping values are otherwise unrestricted (`{'k': '- x'}`
    and `{'k': "''"}` round-trip).
13. Known limitation: deep nesting raises the host `RecursionError`.
    Measured at CPython's default recursion limit (1000, via
    `sys.getrecursionlimit()`; figures scale with the limit and are
    platform/stack-dependent, so treat them as approximate): block-nested
    mappings (`k0:\n  k1:\n    …`) load up to roughly 497 levels with no
    trailing line, but only roughly 247 levels when a trailing sibling
    line (`z: 1` at column 0) follows the deepest block, because the
    trailing line forces every open level to unwind through
    `incorporate_node` before the value is returned. A single line of
    many `- ` markers (`- - - … x`) raises past roughly 121 levels — the
    same cliff applies to a `- ` chain used as a *continuation* line of an
    open text value (`k:\n  a\n  - - … x`), because lexing that line still
    recurses in Parsimonious before the text-context rule re-reads it as
    text (D21). `dumps` of a nested dict raises past roughly 497 levels,
    matching the block-nesting figure; `dumps` writes a nested list inline
    (`[[…]]` as one `- - … x` line), and that output stops loading back
    past roughly 121 levels of list nesting — lower than the block-nesting
    cliff, because it hits the same marker-chain lex recursion as the
    single-line case. `parse()` (grammar-only, no tree building) succeeds
    far beyond either figure — past 4,999 levels in measurement, with no
    cliff found in that range — while `.as_data()` on the same tree starts
    raising `RecursionError` past roughly 498 levels, so `parse()` can
    succeed where `.as_data()` raises. A cyclic structure passed to
    `dumps` raises the same `RecursionError`. Also note the memory cost,
    which nothing bounds: the parse tree takes a few hundred bytes per
    input byte, so an application that parses untrusted input should bound
    its size before calling `loads`.
14. Typing: `loads`/`load` return `SymlData`
    (`str | list[SymlData] | dict[str, SymlData]`) instead of
    `list[Any] | dict[str, Any] | str`, so a typed caller narrows each
    level with `isinstance` before indexing (`r['k']['j']` no longer
    type-checks on the `Any` below the top). `dumps`/`dump` take
    `SymlInput` (`str | list[Any] | dict[str, Any]`), so a
    `dict[str, str]` passes without a cast. Both aliases are exported.
15. `dump` writes through the handle's codec: open it with
    `encoding='utf-8'`. A locale-default handle can write non-UTF-8 bytes
    that `load(open(p, 'rb'))` then rejects.
16. Node-tree and module internals. Only `as_data()` and `as_source()` on
    `parse`'s result are the supported tree surface, but 0.6.2 callers
    could reach the rest through `syml.parsers.parse`: a node's `level` is
    now its own column (not its line's indent); `set_level`, `IndentNode`,
    `Comment`, and `SymlNode.comments` are gone; and `syml.utils`
    (`split_lines`, `get_line`) is deleted.
17. Children must be strictly deeper than their parent, list items
    included: `k:\n- a` raises `OutOfContextNodeError`, with a hint, in
    0.6.2 and still does now — the YAML "indentless sequence" was
    already an error (D25 restores this after an intermediate draft of
    this release briefly allowed it; see item 24 below). A valueless key
    inside a list item (`- key:`)
    takes block content only **deeper than the key's own column**, not
    deeper than the `-`. A line at the key's column is that key's
    **sibling**. This changes one common layout **silently**:
    `- server:\n  host: x` was `[{'server': {'host': 'x'}}]` and is now
    `[{'server': '', 'host': 'x'}]`, with no error. The same layout with a
    list or text under the key (`- key:\n  - x`, `- key:\n  text`) now
    raises `OutOfContextNodeError`. Fix: indent the block past the key
    (`- server:\n    host: x`), which both versions read the same way.
18. §9.0 pre-processing changes values with no error: a CRLF or CR file no
    longer leaves `\r` at the end of every value (`k: v\r\n` was
    `{'k': 'v\r'}`), and one leading U+FEFF is stripped rather than
    joining the first key (`\ufeffkey: v` was `{'\ufeffkey': 'v'}`).

Items 19-24 record the 2026-09-24 D20-D25 language revision
(`SYML-SPEC-REVIEW.md`). Each "was" below compares directly against
0.6.2, the same baseline as items 1-18; none of this ever shipped to a
0.6.2 user as an intermediate release.

19. **Values are text throughout (D21).** Structure is now lexed only at
    a block's first line and inline; once a value's baseline is fixed,
    every later line at or past it is that value's text, whatever it
    would otherwise lex as. Deeper structure-shaped lines after a text
    value now join it, where 0.6.2 read the deeper line as its own
    key-value pair: `note: hello\n  more: text` was the two-key mapping
    `{"note": "hello", "more": "text"}` in 0.6.2, and is now the one-key
    mapping `{"note": "hello\nmore: text"}`. A line indented past a
    sibling that holds an inline value is absorbed silently, too.
    Migration check: for every `key:` or `-` followed by separator
    whitespace and a non-empty inline value, look for a deeper block
    under it that 0.6.2 read as its own key or list item — that block now
    loads as part of the inline value's string. An invisible inline value
    is the hardest instance: a trailing NBSP or other invisible character
    after `key: ` makes a line that reads as bare visually but is not, so
    `server: \xa0\n  host: a` was the two-key mapping
    `{"server": "\xa0", "host": "a"}` in 0.6.2, and is now
    `{"server": "\xa0\nhost: a"}`. Lexing still runs first, so a long
    `- - - …` chain still raises `RecursionError` inside a text value
    (item 13 above).
20. **Blank lines inside a value are paragraph breaks (D22).** A blank
    line between two lines of the same value is now an empty line of that
    value, one per physical blank line, rather than being discarded:
    `k:\n  a\n\n  b` was `"a\nb"` and is now `"a\n\nb"`. Blank lines
    before a value's first line, after its last, or between items/keys
    are still inert. `dumps` writes paragraph breaks back out the same
    way.
21. **Comments are column-0 only (D23).** A line whose first character,
    with no indentation, is `#`, or whose first two characters are `//`,
    is a comment, skipped as if absent anywhere in the document —
    including between two lines of an open value, where it does not add a
    blank line. What still works: column-0 comment lines, file headers
    included. What changes: an **indented** `#`/`//` line is now text,
    not a comment. Inside a value it is kept: `- tag line\n  #winning`
    was `["tag line"]` in 0.6.2 (the comment silently dropped) and is now
    `["tag line\n#winning"]`. At a container's level after its first
    entry it raises. And, **silently**, as the first line of a block it
    makes that block one string: `a:\n  # s\n  b: 1` was the nested
    mapping `{"a": {"b": "1"}}` in 0.6.2, and is now
    `{"a": "# s\nb: 1"}`. And, **silently one level down**, a `#`/`//`
    after `key:` or `-` (YAML's trailing comment) is that key's or item's
    text value and takes in the block under it: `server: # prod\n  host:
    x` was the two-key mapping `{"server": "# prod", "host": "x"}` in
    0.6.2, and is now `{"server": "# prod\nhost: x"}`. To check a file for
    both hazards: search for every **indented** line whose first
    non-space characters are `#` or `//` (changes meaning; fix by moving
    the comment to column 0), and every `key:` or `-` followed by
    separator whitespace and `#` or `//` (changes meaning only when a
    deeper block follows — check what that key loads to; `k: # x` alone
    was already the string `"# x"`). A top-level `isinstance(result,
    dict)` check is not a sufficient migration check: it passes for
    `server: # prod\n  host: x`, whose damage is one level down. A root
    scalar with a line beginning with `#` or `//` is unrepresentable by
    `dumps` (item 12 above).
22. **A tab is separator whitespace (D24).** A tab immediately after
    `key:` or `-` is separator whitespace, same as a space: `k:\tv` and
    `k: \tv` are both `{"k": "v"}`, matching 0.6.2 — this item is a
    confirmation, not a change, of a rule an intermediate draft of this
    release nearly broke and D24 restored. A tab in leading indentation
    still raises `TabIndentationError`, as in 0.6.2. What *is* new: a
    separator tab now counts as exactly one column for the sibling-column
    rule (item 17 above), not a tab stop. `-\tk: v\n  j: w` (`j` at
    column 2, `k`'s own column) was, and still is, the two-key item
    `[{"k": "v", "j": "w"}]`. But `-\tk: v\n        j: w` (`j` visually
    aligned under `k` at an 8-column tab stop) was also two siblings in
    0.6.2, and is now `[{"k": "v\nj: w"}]` — the 8-space line silently
    joins `v` instead, because column 2 is where a sibling must sit.
23. **Only U+0020 is indentation.** No other whitespace-like character —
    NBSP, VT, FF, NEL, U+2028, or any other non-U+0020 character at the
    start of a line — counts as indentation; each is content, where 0.6.2
    treated the Unicode `White_Space` set as indentation. `\xa0k: v` (an
    NBSP-led line, as pasted-from-the-web text often is) was `{"k": "v"}`
    in 0.6.2, and is now the scalar `"\xa0k: v"`. A NBSP, U+200B, or
    U+3000 left after `key: ` or `- ` makes an inline value that silently
    takes in the block under it, the same hazard as item 19's
    invisible-value case. A line holding only a NBSP, form feed, or other
    non-space character is no longer a blank line: `k: v\n \xa0\nj: w`
    was the two-key mapping `{"k": "v", "j": "w"}` in 0.6.2 (the NBSP-only
    line read as blank), and is now `{"k": "v\n\xa0", "j": "w"}` — the
    line silently joins `k`'s value instead. At a container's column such
    a line raises instead of silently joining.
24. Indentless sequences: `k:\n- a` was already `OutOfContextNodeError`
    in 0.6.2, matching item 17 above (D25) — no change from 0.6.2 here,
    though an intermediate draft of this release briefly allowed it
    before D25 restored the strict rule.
25. **New hint (D26).** `OutOfContextNodeError` gains a third hint: when the
    failing line, or the line above (hint (a)'s look-back), is a key or list
    marker missing its trailing space (`port:8080`, `-b`), the message ends
    "Hint: a key or list marker needs a space after it." Grammar unchanged:
    `port:8080` alone (no sibling to raise against) still silently parses as
    text (item 5, D21); the hint only fires where an `OutOfContextNodeError`
    already raises for another reason.
26. **Two more new hints (D27).** `OutOfContextNodeError` gains a fourth and
    fifth hint. When the failing line, after its indentation, starts with
    `#` or `//`, the message ends "Hint: comments must start at column 0;
    an indented '#' line is text." — the most common trigger is commenting
    out a key in place (item 1 already documents that an indented comment
    is text, silently, until a later line collides with it). When the
    failing line is exactly `---` or `...`, the message ends "Hint: SYML has
    no document markers." (item 3). Both hints fire on the failing line
    only (no look-back), on any open-column form, and are checked ahead of
    the D26/US1-8 hints so a spaceless comment (`#port: 80`) is never
    misread as a bad key.
27. **Bug fix: `filename` is now bounded in error rendering.** `.message`'s
    filename prefix and `str(e)`'s `<filename>:` segment are windowed
    through `_truncated_window(filename, center=0)`, the same treatment
    Contract 03 §Bounded rendering (`syml-s9p9.9`/`.14`) already documents
    for a hostile `line_text` or repeated key — this closes the one case
    that treatment missed. In 0.6.2 there was no such bound at all; a
    caller- or attacker-supplied filename of unbounded length (e.g. an
    archive entry path) makes `.message`/`str(e)` scale with the filename's
    own length instead of staying proportional to the fixed 80-code-point
    window (syml-cjk2.5, break-testing round 2 lane 3).

Recursion measurement method (item 13): at CPython's default recursion
limit, bisect the largest depth that loads for (1) `k0:\n  k1:\n    …`
with no trailing line, (2) the same plus a trailing `z: 1` at column 0,
(3) `- - … - x` on one line, (4) `dumps` of a nested dict, (5) the same
`- ` chain as a continuation line of a text value, confirming it raises
where (3) does, and (6) `dumps` of a nested list, bisected on whether the
output loads back; also the largest depth at which `parse()` succeeds and
the smallest depth past which `.as_data()` on that tree raises.
