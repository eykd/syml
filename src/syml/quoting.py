r"""Quoted-string decoding for SYML documents (§4.7, Contract 04, US6).

:class:`QuotedStringDefect` is a real, fully-specified module-private
signal. :func:`decode_double_quoted` decodes the §4.7 escape table (``\n``,
``\t``, ``\r``, ``\\``, ``\/``, ``\"``, ``\uXXXX``, ``\UXXXXXXXX``);
every escape it receives is syntactically valid per the grammar.
:func:`decode_single_quoted` strips the surrounding quotes and decodes the
``''`` -> one apostrophe escape (D2); backslashes stay literal.
:func:`diagnose_malformed` reports the first invalid/incomplete escape in a
candidate quoted literal that failed to match `quoted_value` (Contract 04
§What the quote-guard reports), or `None` when the value is merely
unterminated.
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
_HEX_DIGITS = frozenset('0123456789abcdefABCDEF')

_MAX_CODE_POINT = 0x10FFFF
_SURROGATE_RANGE = range(0xD800, 0xE000)


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
        code_point = int(hex_digits, 16)
        if code_point > _MAX_CODE_POINT or code_point in _SURROGATE_RANGE:
            escape = f'\\{escape_char}{hex_digits}'
            raise QuotedStringDefect(escape, code_point)
        result.append(chr(code_point))
        index += 2 + width
    return ''.join(result)


def diagnose_malformed(text: str) -> str | None:
    """Diagnose why `text` failed to match `quoted_value` (Contract 04 §What the quote-guard reports).

    A left-to-right scan from the opening quote for the first invalid or
    incomplete escape. Returns that escape's text, or `None` if the value
    is merely unterminated. Single-quoted values have no escapes, so the
    only reachable diagnosis for them is unterminated (`None`).
    """
    if not text.startswith('"'):
        return None
    index = 1
    length = len(text)
    while index < length:
        char = text[index]
        if char != '\\':
            index += 1
            continue
        if index + 1 >= length:
            return '\\'
        escape_char = text[index + 1]
        if escape_char in _SIMPLE_ESCAPES:
            index += 2
            continue
        if escape_char in _HEX_ESCAPE_WIDTHS:
            width = _HEX_ESCAPE_WIDTHS[escape_char]
            digits = ''
            pos = index + 2
            while len(digits) < width and pos < length and text[pos] in _HEX_DIGITS:
                digits += text[pos]
                pos += 1
            if len(digits) == width:
                index = pos
                continue
            return f'\\{escape_char}{digits}'
        return f'\\{escape_char}'
    return None
