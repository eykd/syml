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
    if data == '':
        return ''
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
    return match.end == len(k)


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
    if scalar_lines[0].startswith('\x00INLINE'):
        return [f"{marker} {scalar_lines[0][len('\x00INLINE'):]}", *scalar_lines[1:]]
    if len(scalar_lines) == 1:
        return [f'{marker} {scalar_lines[0].lstrip(' ')}']
    return [marker, *scalar_lines]


INLINE_FIRST = False

def _render_scalar_lines(value, indent, position):
    text = str.__str__(value)
    if not text:
        return []
    if _CONTROL_CHAR_PATTERN.search(text):
        raise _unrepresentable(text, 'control')
    lines = text.split('\n')
    if len(lines) > 1 and (lines[0] == '' or lines[-1] == ''):
        raise _unrepresentable(text, 'begins or ends with blank line')
    for ln in lines:
        run = ln[: len(ln) - len(ln.lstrip(' \t'))]
        if ln and run == ln:
            raise _unrepresentable(text, 'whitespace-only line')
        if '\t' in run:
            raise _unrepresentable(text, 'tab in leading whitespace')
    if position != 'root' and lines[0][:1] == ' ':
        raise _unrepresentable(text, 'begins with space')
    first_structure = _lexes_as_structure(lines[0])
    if position == 'list' and first_structure:
        raise _unrepresentable(text, 'list structure')
    if position == 'root' and first_structure:
        raise _unrepresentable(text, 'root structure')
    pad = ' ' * indent
    out = [f'{pad}{ln}' if ln else '' for ln in lines]
    if position == 'mapping' and len(lines) > 1 and first_structure:
        if not INLINE_FIRST:
            raise _unrepresentable(text, 'mapping block structure')
        return ['\x00INLINE' + lines[0]] + out[1:]
    return out


def _lexes_as_structure(line):
    content = line.lstrip(' ')
    try:
        _GRAMMAR['structure'].parse(content)
    except RecursionError:
        return True
    except parsimonious.exceptions.ParseError:
        return False
    return True
