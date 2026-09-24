"""Serialize SYML-representable data back to SYML text (Contract 07, §11.2.1)."""

from __future__ import annotations

import re
from typing import IO, TYPE_CHECKING, Literal

import parsimonious

from . import nodes, parsers
from .exceptions import UnrepresentableValueError

if TYPE_CHECKING:  # pragma: nocover
    from .basetypes import SymlInput

_GRAMMAR = parsers.SymlParser.grammar

#: Every C0/C1 control character except LF (a line break) and TAB (permitted
#: inside a value, §4.2 rule 3 / §7.5).
_CONTROL_CHAR_PATTERN = re.compile('[\x00-\x08\x0b-\x1f\x7f-\x9f]')

_BOM = '﻿'

_COMMENT_MARKERS = ('#', '//')

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
    indentation, no blank lines, exactly one trailing newline, keys in
    insertion order. The empty string serializes to the empty document ''.
    If the output would begin with U+FEFF, one extra U+FEFF is prepended,
    because loads strips exactly one leading mark. A str subclass, such as
    a (str, Enum) member, is written as its string value.
    """
    if isinstance(data, str):
        rendered_lines = _render_scalar_lines(str.__str__(data), 0, 'root')
    else:
        rendered_lines = _render_value_lines(data, 0)
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
    """Return whether `k` can be written as a SYML mapping key (§11.2.3, D1, D19, M8).

    False for a key that contains whitespace or ':', is the empty string,
    begins with '#' or '//', contains an uppercase code point (D19), or
    otherwise fails to fully match the `key` grammar rule (e.g. a C0/C1
    control character, per §4.5).
    """
    try:
        match = _GRAMMAR['key'].match(k)
    except parsimonious.exceptions.ParseError:
        return False
    return match.end == len(k) and not k.startswith(_COMMENT_MARKERS) and not parsers.key_has_uppercase(k)


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
        if not isinstance(key, str):
            message = f'{key!r} is not a valid SYML mapping key (must be str)'
            raise TypeError(message, key)
        key_str = str.__str__(key)
        if not key_is_representable(key_str):
            message = f'{key_str!r} is not representable as a SYML mapping key (§11.2.3)'
            raise UnrepresentableValueError(message, key_str)
        if isinstance(value, str):
            lines.extend(_with_marker(f'{pad}{key_str}:', _render_scalar_lines(value, indent + 2, 'mapping')))
        else:
            lines.append(f'{pad}{key_str}:')
            lines.extend(_render_value_lines(value, indent + 2))
    return lines


def _render_list_lines(items: list[object], indent: int) -> list[str]:
    """Render a list's `- item` lines at `indent` spaces."""
    pad = ' ' * indent
    lines: list[str] = []
    for item in items:
        if isinstance(item, str):
            lines.extend(_with_marker(f'{pad}-', _render_scalar_lines(item, indent + 2, 'list')))
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
    written inline; a multi-line value, or any root scalar, is written as
    bare lines, which must each survive being lexed on their own (§5.1
    rule 6). Relative indentation past the first line is preserved by §5.3,
    so only the first line's leading whitespace is restricted.
    """
    text = str.__str__(value)
    if not text:
        return []
    if _CONTROL_CHAR_PATTERN.search(text):
        raise _unrepresentable(text, 'contains a control character')
    lines = text.split('\n')
    if lines[0][:1] in (' ', '\t'):
        raise _unrepresentable(text, 'begins with whitespace')
    block = position == 'root' or len(lines) > 1
    if block:
        for line in lines:
            _check_block_line(text, line)
    elif position == 'list' and _lexes_as_structure(lines[0]):
        raise _unrepresentable(text, 'a list item value would lex as structure')
    pad = ' ' * indent
    return [f'{pad}{line}' for line in lines]


def _check_block_line(text: str, line: str) -> None:
    """Raise unless `line` can stand as one physical line of a block value (§5.1, §5.3)."""
    content = line.lstrip(' ')
    if not content:
        raise _unrepresentable(text, 'contains a blank or whitespace-only line')
    if content.startswith('\t'):
        raise _unrepresentable(text, 'a line begins with a tab')
    if content.startswith(_COMMENT_MARKERS):
        raise _unrepresentable(text, 'a line begins with a comment marker')
    if _lexes_as_structure(content):
        raise _unrepresentable(text, 'a line would lex as structure')


def _lexes_as_structure(line: str) -> bool:
    """Does the single physical line `line` parse as a list item, key-value pair, or section?

    Parses `line` with the real parser, so D19's no-uppercase key rule is
    honoured (`Listen: here` is text, `listen: here` is structure). A
    `- `-led run deep enough to exhaust the parser's recursion is treated
    as structure, since it cannot be re-read at all.
    """
    try:
        root = parsers.parse(line)
    except RecursionError:
        return True
    return bool(root.children) and not isinstance(root.children[0], nodes.TextLeafNode)
