r"""Quoted-string decoding for SYML documents (§4.7, Contract 04, US6).

:class:`QuotedStringDefect` is a real, fully-specified module-private
signal. :func:`decode_double_quoted` decodes the §4.7 escape table (``\n``,
``\t``, ``\r``, ``\\``, ``\/``, ``\"``, ``\uXXXX``, ``\UXXXXXXXX``);
every escape it receives is syntactically valid per the grammar.
:func:`decode_single_quoted` strips the surrounding quotes and decodes the
``''`` -> one apostrophe escape (D2); backslashes stay literal.
``diagnose_malformed`` belongs to a later US6 leaf and is not stubbed here.
"""

from __future__ import annotations


class QuotedStringDefect(ValueError):  # noqa: N818 -- private signal, never reaches a caller
    """Raised by `decode_double_quoted`; converted by `visit_quoted_value` (Contract 05)."""

    def __init__(self, escape: str, code_point: int) -> None:
        """Store the offending escape text and out-of-range/surrogate code point."""
        super().__init__(escape, code_point)
        self.escape = escape
        self.code_point = code_point


def decode_single_quoted(raw: str) -> str:
    """Decode a '...' literal (Contract 04). `raw` includes the surrounding quotes."""
    return raw[1:-1].replace("''", "'")


_SIMPLE_ESCAPES = {
    '\\': '\\',
    '/': '/',
    '"': '"',
    'n': '\n',
    't': '\t',
    'r': '\r',
}

_HEX_ESCAPE_WIDTHS = {'u': 4, 'U': 8}


def decode_double_quoted(raw: str) -> str:
    """Decode a "..." literal per the §4.7 escape table (Contract 04)."""
    body = raw[1:-1]
    result: list[str] = []
    index = 0
    length = len(body)
    while index < length:
        char = body[index]
        if char != '\\':
            result.append(char)
            index += 1
            continue
        escape_char = body[index + 1]
        if escape_char in _SIMPLE_ESCAPES:
            result.append(_SIMPLE_ESCAPES[escape_char])
            index += 2
            continue
        width = _HEX_ESCAPE_WIDTHS[escape_char]
        hex_digits = body[index + 2 : index + 2 + width]
        result.append(chr(int(hex_digits, 16)))
        index += 2 + width
    return ''.join(result)
