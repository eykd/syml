"""Quoted-string decoding for SYML documents (§4.7, Contract 04, US6).

:class:`QuotedStringDefect` is a real, fully-specified module-private
signal. :func:`decode_double_quoted` is a stub that raises
``NotImplementedError`` until US6 implements the escape table.
:func:`decode_single_quoted` strips the surrounding quotes only (D2); its
``''`` -> one apostrophe and literal-backslash handling belong to a later
US6 leaf. ``diagnose_malformed`` belongs to a later US6 leaf and is not
stubbed here.
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


def decode_double_quoted(raw: str) -> str:
    """Decode a "..." literal per the §4.7 escape table (Contract 04). Not yet implemented (US6)."""
    message = f'decode_double_quoted is not yet implemented (US6): {raw!r}'
    raise NotImplementedError(message)
