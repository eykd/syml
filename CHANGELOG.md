Changelog
=========

## 1.0.0 (2026-09-24)

Migration notes for a 0.6.2 user upgrading to 1.0.0. Every user-visible
change from 0.6.2 is listed below, numbered to match Contract 09's audit
(`specs/001-syml-1-0-conformance/contracts/09-release-text.md` § FR-015).

1. Absent values: `None` → `""`, at every depth.
2. Tabs in indentation → `TabIndentationError`.
3. Duplicate keys → `DuplicateKeyError`.
4. Keys may not contain an uppercase (or titlecase) character (D19).
   `Name: x` is now the scalar text `Name: x`, not a mapping — breaking
   vs 0.6.2, and **silent** for a one-line document. In a mapping it
   raises instead: `name: a\nName: b` is `OutOfContextNodeError`, because
   the second line is text at a mapping's level. Rename such keys to
   lowercase (`name:`). `dumps({'Name': 'x'})` raises
   `UnrepresentableValueError`. The check is Unicode General_Category
   `Lu`/`Lt` on any code point, so `É` disqualifies a key while `名前` or
   `Ⅻ` does not. Quoted strings remain unsupported, as in 0.6.2 (D18): a
   leading `'` or `"` is ordinary text everywhere, and `title: "Hello"`
   is the value `"Hello"` with its quotation marks, just as it was.
5. `-` / `key:value` fallthrough: bare `-` takes a block value;
   `key:value` is a scalar instead of raising.
6. Sibling indentation is now exact (`==`), and a closed key/item accepts
   nothing.
7. Multiline values preserve indentation past the baseline; a
   below-baseline line terminates the value. A root scalar's baseline is
   column 0, so an indented root scalar keeps its indentation: `  hello`
   was `'hello'` and is `'  hello'`.
8. Parsimonious exceptions no longer escape; everything is a `ParseError`.
9. `ParseError` gains `.message` / `.position` / `.line_text`, and its
   constructor now requires them: `ParseError('msg')` (valid in 0.6.2,
   where it was a bare `ValueError`) is a `TypeError`. `.message` is
   prefixed with the filename when there is one.
10. `Pos` coordinates now refer to the **original** text. `Source` still
    equals a `str` with the same text, but no longer equals a non-`str`
    (`Source('1') == 1` was `True`). `Source.from_node` takes
    `(pnode, line, position_map, filename)` instead of `(pnode, filename)`;
    `Pos.from_str_index` and `Source.from_text` count only `\n` as a line
    break (U+2028, U+0085 and the rest no longer start a line); and
    `Source + str` now counts the joining `\n` in `end.index` and accepts
    `''`.
11. `load()` accepts binary streams and decodes them as strict UTF-8;
    invalid UTF-8 → `EncodingError`. A text handle decodes with its own
    codec before `load` sees the text: a failure there is also
    `EncodingError`, but a handle in another encoding can decode UTF-8
    bytes to the wrong characters with no error (cp1252 reads `é` as `Ã©`),
    so strict UTF-8 needs `open(p, 'rb')` or `encoding='utf-8'`. `filename`
    now defaults to a `str` or path-like `file_obj.name`. `Pos.index` from
    a default `open(p)` text handle is an offset into newline-translated
    text; editor-grade positions need `open(p, 'rb')` or
    `open(p, encoding='utf-8', newline='')`.
12. New: `dumps`, `dump`, and `parse` promoted to a public export.
    `syml.parsers.SymlParser` now takes a preprocessed `Document` rather
    than a `filename` and is no longer a whole-document entry point
    (per-line lexing): call `syml.parse` instead. `dumps` writes every
    string as literal text: a single-line value inline, a multi-line
    string (and any root scalar) in block form with each line indented
    beneath its key or `-`. It raises `UnrepresentableValueError` for the
    set in §11.2.1: a control character other than LF/TAB (so `\r`, NUL),
    a value whose first line begins with a space or tab, a blank,
    tab-initial, `#`/`//`-initial, or structure-shaped line inside a
    multi-line value (honouring D19: `Listen: x` is text, `listen: x` is
    structure), and a single-line list item that would lex as structure
    (`['- x']`, `['key: v']`, `['-']`). Single-line mapping values are
    otherwise unrestricted (`{'k': '- x'}` and `{'k': "''"}` round-trip).
13. Known limitation: deep nesting raises the host `RecursionError` — past
    roughly 500 levels of **block** nesting (one level per line), but past
    only roughly 120 levels of **inline** nesting on a single line
    (`- - - … x`, a ~250-byte input) at CPython's default recursion limit,
    because lexing that one line recurses in Parsimonious. A string of
    the form `'- - … x'` is `UnrepresentableValueError` at a list
    position (it would lex as structure) and is written literally, with
    no lexing, at a mapping position. Deeply nested *data*
    (roughly 1,000 levels of lists or mappings) may raise `RecursionError`
    from `dumps` as well. The figures scale with
    `sys.getrecursionlimit()`: about limit/2 block levels and limit/8
    inline levels. A cyclic structure passed to `dumps` raises the same
    `RecursionError`. Also note the memory cost, which nothing bounds:
    the parse tree takes a few hundred bytes per input byte, so an
    application that parses untrusted input should bound its size before
    calling `loads`.
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
    now its own column (not its line's indent), and `set_level` and
    `IndentNode` are gone; `incorporate_node` and `can_add_node` take a
    second `doc` argument; `source` is a required constructor field
    instead of being derived from `pnode`; `KeyLeafNode.key` is removed
    (use `as_source()`); nodes no longer store their Parsimonious `pnode`;
    and `syml.utils` (`split_lines`, `get_line`) is deleted.
17. A valueless key inside a list item (`- key:`) takes block content only
    **deeper than the key's own column**, not deeper than the `-`. A line
    at the key's column is that key's **sibling**. This changes one
    common layout **silently**: `- server:\n  host: x` was
    `[{'server': {'host': 'x'}}]` and is now
    `[{'server': '', 'host': 'x'}]`, with no error. The same layout with a
    list or text under the key (`- key:\n  - x`, `- key:\n  text`) now
    raises `OutOfContextNodeError`. Fix: indent the block past the key
    (`- server:\n    host: x`), which both versions read the same way.
18. §9.0 pre-processing changes values with no error: a CRLF or CR file no
    longer leaves `\r` at the end of every value (`k: v\r\n` was
    `{'k': 'v\r'}`), and one leading U+FEFF is stripped rather than
    joining the first key (`\ufeffkey: v` was `{'\ufeffkey': 'v'}`).
