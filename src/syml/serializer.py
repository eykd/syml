"""Serialize SYML-representable data back to SYML text (Contract 07)."""

from __future__ import annotations

from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: nocover
    from .basetypes import SymlInput


def dumps(data: SymlInput) -> str:
    r"""Serialize `data` to SYML text such that `loads` inverts it.

    Raises UnrepresentableValueError for a SYML value with no encoding
    (§11.2.2-.4) and TypeError for anything that is not str, list, or dict,
    including a non-str mapping key.

    Output format (an implementation choice, not conformance): two-space
    indentation, no blank lines, exactly one trailing newline, keys in
    insertion order. The empty string serializes to the empty document ''.
    When quoting is required, single quotes are preferred. At a list-item
    position, a quoted value that would re-read as a mapping is written
    double-quoted with every ':' escaped as :. If the output would
    begin with U+FEFF, one extra U+FEFF is prepended, because loads strips
    exactly one leading mark. A str subclass, such as a (str, Enum)
    member, is written as its string value.
    """
    return '\n'.join(_render_value_lines(data, 0)) + '\n'


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
    # Implemented and tested by the dedicated dump() single-write-semantics
    # Red/Green pair (syml-x0m.5.8.20/.21); this Green task scopes only the
    # dumps() type contract.
    raise NotImplementedError  # pragma: nocover


def _not_representable(value: object) -> TypeError:
    """Build the TypeError raised for a value that is not str, list, or dict."""
    message = f'{value!r} is not representable in SYML (not str, list, or dict)'
    return TypeError(message, value)


def _render_value_lines(value: object, indent: int) -> list[str]:
    """Dispatch `value` to its type's line renderer, or raise TypeError."""
    if isinstance(value, dict):
        return _render_mapping_lines(value, indent)
    if isinstance(value, list):
        return _render_list_lines(value, indent)
    if isinstance(value, str):
        return [str.__str__(value)]
    raise _not_representable(value)


def _render_mapping_lines(mapping: dict[object, object], indent: int) -> list[str]:
    """Render a mapping's `key: value` lines at `indent` spaces."""
    pad = ' ' * indent
    lines: list[str] = []
    for key, value in mapping.items():
        if not isinstance(key, str):
            message = f'{key!r} is not a valid SYML mapping key (must be str)'
            raise TypeError(message, key)
        key_str = str.__str__(key)
        value_lines = _render_value_lines(value, indent + 2)
        if isinstance(value, str):
            lines.append(f'{pad}{key_str}: {value_lines[0]}')
        else:
            lines.append(f'{pad}{key_str}:')
            lines.extend(value_lines)
    return lines


def _render_list_lines(items: list[object], indent: int) -> list[str]:
    """Render a list's `- item` lines at `indent` spaces."""
    pad = ' ' * indent
    lines: list[str] = []
    for item in items:
        item_lines = _render_value_lines(item, indent + 2)
        if isinstance(item, str):
            lines.append(f'{pad}- {item_lines[0]}')
        else:
            lines.append(f'{pad}- {item_lines[0].lstrip()}')
            lines.extend(item_lines[1:])
    return lines
