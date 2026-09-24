"""Quoted-string decoding for SYML documents (§4.7, Contract 04, US6).

Only the pieces Contract 05's "decoder failures cross the visitor as
ParseErrors" leaf needs exist here so far: :class:`QuotedStringDefect` (a
real, fully-specified module-private signal) and a stub
:func:`decode_double_quoted` that raises ``NotImplementedError`` until US6
implements the escape table. ``decode_single_quoted`` and
``diagnose_malformed`` belong to later US6 leaves and are not stubbed here.
"""

from __future__ import annotations


class QuotedStringDefect(ValueError):  # noqa: N818 -- private signal, never reaches a caller
    """Raised by `decode_double_quoted`; converted by `visit_quoted_value` (Contract 05)."""

    def __init__(self, escape: str, code_point: int) -> None:
        """Store the offending escape text and out-of-range/surrogate code point."""
        super().__init__(escape, code_point)
        self.escape = escape
        self.code_point = code_point


def decode_double_quoted(raw: str) -> str:
    """Decode a "..." literal per the §4.7 escape table (Contract 04). Not yet implemented (US6)."""
    message = f'decode_double_quoted is not yet implemented (US6): {raw!r}'
    raise NotImplementedError(message)
