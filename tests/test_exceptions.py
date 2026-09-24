"""Tests for src/syml/exceptions.py."""

from __future__ import annotations

from syml.basetypes import Pos
from syml.exceptions import ParseError


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
