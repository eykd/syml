"""Serialize SYML-representable data back to SYML text (Contract 07, §11.2.1)."""

from __future__ import annotations

import re
from typing import IO, TYPE_CHECKING, Literal

from . import nodes, parsers
from .basetypes import Source
from .exceptions import UnrepresentableValueError

if TYPE_CHECKING:  # pragma: nocover
    from .basetypes import SymlInput

#: Every C0/C1 control character except LF (a line break) and TAB (permitted
#: inside a value, §4.2 rule 3 / §7.5).
_CONTROL_CHAR_PATTERN = re.compile('[\x00-\x08\x0b-\x1f\x7f-\x9f]')

_BOM = '﻿'

_COMMENT_MARKERS = ('#', '//')

#: Mirrors the grammar's `key` rule (§4.5): ASCII, lowercase, leading letter.
_KEY_PATTERN = re.compile(r'[a-z][a-z0-9_-]*')

#: A leading run of `- ` (or `-\t`) markers, with an optional trailing bare
#: `-`, matched against a later block line after its leading spaces (§11.2.1
#: item 2, R-05, R-17). Always matches (possibly the empty string at index 0).
_MARKER_CHAIN_PATTERN = re.compile(r'(?:-[ \t]+)*-?')

#: The recursion guard for a later block line's leading marker chain: a fixed
#: count, never a parse, because the lex cliff moves with the caller's own
#: stack (about 122 markers at a shallow stack, about 60 with 500 frames
#: already in use). 32 markers costs `loads` roughly a quarter of the default
#: recursion limit.
MAX_LATER_LINE_MARKERS = 32

Position = Literal['root', 'mapping', 'list']


def dumps(data: SymlInput) -> str:
    """Serialize `data` to SYML text such that `loads` inverts it.

    Values are literal (D18): no quoting exists, so a string is written as
    the text on the page. A string containing a newline is written in block
    form, one physical line per line of the value, indented two spaces past
    its key or list marker (§5.1, §5.3). Raises UnrepresentableValueError
    for a value with no encoding under those rules (§11.2.1-.3) and
    TypeError for anything that is not str, list, or dict, including a
    non-str mapping key.

    Output format (an implementation choice, not conformance): two-space
    indentation, keys in insertion order, exactly one trailing newline for
    any non-empty output, none for the empty document. A literal blank line
    inside a value (a paragraph break, D22) is written as an empty physical
    line with no indentation. The empty string serializes to the empty
    document ''.
    If the output would begin with U+FEFF, one extra U+FEFF is prepended,
    because loads strips exactly one leading mark. A str subclass, such as
    a (str, Enum) member, is written as its string value. A `Source` (as
    returned by `as_source()`) is accepted anywhere a `str` key or scalar
    is, read via its `.text` before any type check (FR-014), so
    `dumps(parse(t).as_source())` round-trips like `dumps(parse(t).as_data())`.
    """
    text = _scalar_text(data)
    rendered_lines = _render_scalar_lines(text, 0, 'root') if text is not None else _render_value_lines(data, 0)
    if not rendered_lines:
        return ''
    rendered = '\n'.join(rendered_lines) + '\n'
    if rendered.startswith(_BOM):
        rendered = _BOM + rendered
    return rendered


def dump(data: SymlInput, file_obj: IO[str]) -> None:
    """Serialize with dumps, then write the whole result in one write() call.

    If dumps raises, nothing is written. SYML documents are UTF-8
    (§13.3): open the handle with encoding='utf-8'. dump writes through the
    handle's own codec and does not check it, so a locale-default handle
    can write bytes that are not UTF-8. A lone surrogate in any string is
    written literally (SYML has no escape for one); a strict UTF-8 stream
    then raises its own UnicodeEncodeError, not a SYML error. A file
    reopened with encoding='utf-8-sig' loses one leading U+FEFF to the
    codec and one to §9.0, so a value's own leading U+FEFF does not survive
    that round trip; writing with 'utf-8-sig' adds a mark instead.
    """
    file_obj.write(dumps(data))


def key_is_representable(k: str) -> bool:
    """Return whether `k` can be written as a SYML mapping key (§11.2.3, §4.5).

    The key grammar rule is `[a-z][a-z0-9_-]*` (ASCII, lowercase, leading
    letter), so this is a straight `re.fullmatch` against that pattern.
    """
    return re.fullmatch(_KEY_PATTERN, k) is not None


def _scalar_text(value: object) -> str | None:
    r"""Return `value`'s text if it is a `str` or a `Source`, else None (FR-014).

    Reads a `Source`'s `.text` before any type check, so a `Source` mapping
    key or scalar value round-trips exactly like the `str` it carries
    (US3-8): `dumps(parse('k: v').as_source())` == `'k: v\n'`. A `str`
    subclass is read through `str.__str__` so an overridden `__str__` (e.g.
    a `(str, Enum)` member) never substitutes its own text.
    """
    if isinstance(value, Source):
        return value.text
    if isinstance(value, str):
        return str.__str__(value)
    return None


def _not_representable(value: object) -> TypeError:
    """Build the TypeError raised for a value that is not str, list, or dict."""
    message = f'{value!r} is not representable in SYML (not str, list, or dict)'
    return TypeError(message, value)


def _unrepresentable(text: str, why: str) -> UnrepresentableValueError:
    """Build the UnrepresentableValueError for a scalar `text` (§11.2.1)."""
    message = f'{text!r} is not representable in SYML ({why}, §11.2.1)'
    return UnrepresentableValueError(message, text)


def _render_value_lines(value: object, indent: int) -> list[str]:
    """Dispatch a container `value` to its type's line renderer, or raise TypeError.

    Scalars are rendered by the container renderers themselves, through
    `_render_scalar_lines`, because their layout depends on the position.
    """
    if isinstance(value, dict):
        _require_nonempty_container(value, 'mapping')
        return _render_mapping_lines(value, indent)
    if isinstance(value, list):
        _require_nonempty_container(value, 'list')
        return _render_list_lines(value, indent)
    raise _not_representable(value)


def _require_nonempty_container(value: dict[object, object] | list[object], kind: str) -> None:
    """Raise UnrepresentableValueError (§11.2.2) if `value` is an empty container."""
    if not value:
        message = f'{value!r} is not representable in SYML (empty {kind}, §11.2.2)'
        raise UnrepresentableValueError(message, value)


def _render_mapping_lines(mapping: dict[object, object], indent: int) -> list[str]:
    """Render a mapping's `key: value` lines at `indent` spaces."""
    pad = ' ' * indent
    lines: list[str] = []
    for key, value in mapping.items():
        key_str = _scalar_text(key)
        if key_str is None:
            message = f'{key!r} is not a valid SYML mapping key (must be str)'
            raise TypeError(message, key)
        if not key_is_representable(key_str):
            message = f'{key_str!r} is not representable as a SYML mapping key (§11.2.3)'
            raise UnrepresentableValueError(message, key_str)
        value_text = _scalar_text(value)
        if value_text is not None:
            lines.extend(_with_marker(f'{pad}{key_str}:', _render_scalar_lines(value_text, indent + 2, 'mapping')))
        else:
            lines.append(f'{pad}{key_str}:')
            lines.extend(_render_value_lines(value, indent + 2))
    return lines


def _render_list_lines(items: list[object], indent: int) -> list[str]:
    """Render a list's `- item` lines at `indent` spaces."""
    pad = ' ' * indent
    lines: list[str] = []
    for item in items:
        item_text = _scalar_text(item)
        if item_text is not None:
            lines.extend(_with_marker(f'{pad}-', _render_scalar_lines(item_text, indent + 2, 'list')))
        else:
            item_lines = _render_value_lines(item, indent + 2)
            # Rule G: exactly one space between `-` and an inline mapping's key.
            lines.append(f'{pad}- {item_lines[0].lstrip()}')
            lines.extend(item_lines[1:])
    return lines


def _with_marker(marker: str, scalar_lines: list[str]) -> list[str]:
    """Attach a scalar's rendered lines to its `key:`/`-` marker.

    An empty value is the bare marker (rule A); a single-line value goes
    inline after one space; a multi-line value goes in block form under the
    marker, already indented by `_render_scalar_lines`.
    """
    if not scalar_lines:
        return [marker]
    if len(scalar_lines) == 1:
        return [f'{marker} {scalar_lines[0].lstrip(' ')}']
    return [marker, *scalar_lines]


def _render_scalar_lines(value: str, indent: int, position: Position) -> list[str]:
    """Render one string at `indent` for `position`, or raise UnrepresentableValueError (§11.2.1).

    Returns no lines for the empty string (rule A: the position's empty
    convention). A single-line value at a mapping or list position is
    written inline (rule B); a multi-line value, or any root scalar, is
    written as bare lines in block form (rule C). Once a block value's
    baseline is fixed, only its *first* line is restricted the way rule B's
    single-line value is (no leading space at a mapping/list position, no
    structure-shaped lex); every later line is free to lex as anything and
    still round-trips as text (D21), except the fixed 32-marker recursion
    guard (item 2's later-line clause) and, for a root scalar only, a
    column-0 `#`/`//` line (item 9, D23).
    """
    text = str.__str__(value)
    if not text:
        return []
    if _CONTROL_CHAR_PATTERN.search(text):
        raise _unrepresentable(text, 'contains a control character')
    lines = text.split('\n')
    multiline = len(lines) > 1
    if multiline and (lines[0] == '' or lines[-1] == ''):
        raise _unrepresentable(text, 'begins or ends with a blank line')
    if position in ('mapping', 'list') and not multiline:
        _check_inline_first_line(text, lines[0], position)
    else:
        for index, line in enumerate(lines):
            _check_block_line(text, line, index, position)
    pad = ' ' * indent
    return [f'{pad}{line}' if line else '' for line in lines]


def _check_inline_first_line(text: str, line: str, position: Position) -> None:
    """Raise unless `line` can stand as rule B's single-line inline value."""
    if line[:1] in (' ', '\t'):
        raise _unrepresentable(text, 'begins with whitespace')
    if position == 'list' and _lexes_as_structure(line):
        raise _unrepresentable(text, 'a list item value would lex as structure')


def _check_block_line(text: str, line: str, index: int, position: Position) -> None:
    """Raise unless `line` can stand as one physical line of a block value (§5.1, §5.3)."""
    leading = _leading_whitespace_run(line)
    if '\t' in leading:
        raise _unrepresentable(text, 'a line begins with a tab')
    if leading and len(leading) == len(line):
        raise _unrepresentable(text, 'contains a blank or whitespace-only line')
    if position == 'root' and line.startswith(_COMMENT_MARKERS):
        raise _unrepresentable(text, 'a line begins with a comment marker')
    if index == 0:
        if position in ('mapping', 'list') and line[:1] == ' ':
            raise _unrepresentable(text, 'begins with whitespace')
        if _lexes_as_structure(line):
            raise _unrepresentable(text, 'a line would lex as structure')
    elif _later_line_marker_count(line) > MAX_LATER_LINE_MARKERS:
        raise _unrepresentable(text, 'a later line has too many leading "- " markers')


def _leading_whitespace_run(line: str) -> str:
    """Return the run of spaces and tabs at the start of `line`."""
    index = 0
    while index < len(line) and line[index] in ' \t':
        index += 1
    return line[:index]


def _later_line_marker_count(line: str) -> int:
    """Count leading `- ` markers in `line` after its leading spaces (§11.2.1 item 2).

    A count, never a parse (R-17): the recursion cliff moves with the
    caller's own stack, so this never risks a `RecursionError` and never
    depends on where `dumps` is called from.
    """
    match = _MARKER_CHAIN_PATTERN.match(line.lstrip(' '))
    return match.group().count('-') if match else 0


def _lexes_as_structure(line: str) -> bool:
    """Does the single physical line `line` parse as a list item, key-value pair, or section?

    Parses `line` with the real grammar directly (`parsers.SymlParser`), not
    `parsers.parse`, so §9.0 pre-processing never runs on the isolated line:
    a leading U+FEFF is judged as the line's own content, not stripped as a
    document-level BOM (US3-5, FR-006). D19's no-uppercase key rule is still
    honoured (`Listen: here` is text, `listen: here` is structure). A
    `- `-led run deep enough to exhaust the parser's recursion is treated
    as structure, since it cannot be re-read at all.
    """
    try:
        root = parsers.SymlParser(filename=None, position_map=None).parse(line)
    except RecursionError:
        return True
    return bool(root.children) and not isinstance(root.children[0], nodes.TextLeafNode)
