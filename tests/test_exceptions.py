"""Tests for src/syml/exceptions.py."""

from __future__ import annotations

import pytest

from syml.basetypes import Pos
from syml.exceptions import ParseError
from syml.preprocess import encoding_error


class TestParseErrorAttributeContract:
    """Contract 05 §Attribute contract (R-03).

    `ParseError.__init__` takes `message`, `position`, `line_text` and stores
    them as named attributes, while still preserving `.args` for existing
    `except ParseError as e: e.args[1]`-style code.
    """

    def test_parse_error_stores_message_position_and_line_text(self) -> None:
        """The three named attributes carry exactly the constructor arguments."""
        position = Pos(index=3, line=1, column=3)

        error = ParseError('Failed to incorporate a node', position, 'foo')

        assert error.message == 'Failed to incorporate a node'
        assert error.position == position
        assert error.line_text == 'foo'


class TestEncodingErrorPositionDerivation:
    """Contract 05 §`EncodingError` position derivation (R-04).

    `UnicodeDecodeError.start` is a byte offset, not a code-point index;
    `encoding_error` must convert it to original-text `Pos` coordinates.
    """

    def test_encoding_error_converts_byte_offset_to_code_point_position(self) -> None:
        """Assert converted `Pos` and `line_text` derived from a byte offset.

        A multi-byte char and a CRLF before the bad byte make byte- and
        code-point-counting diverge, so a naive `Pos(err.start, ...)`
        implementation cannot pass this test.
        """
        raw = b'k\xc3\xa9: v\r\nx: \xff'
        with pytest.raises(UnicodeDecodeError) as exc_info:
            raw.decode('utf-8')
        err = exc_info.value

        result = encoding_error(err, None)

        assert result.position == Pos(index=10, line=2, column=3)
        assert result.line_text == 'x: '
        assert result.message == 'Invalid encoding'
